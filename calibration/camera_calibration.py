"""Ordinary USB camera ChArUco calibration; capture or use saved raw images."""
import argparse
from pathlib import Path
import cv2
import numpy as np
import yaml
from calibration.board import DEFAULT_BOARD, load_board, detect_points
from tracking.calibration import calibration_data, load_calibration


def solve_views(objects, images, size):
    if len(objects) < 15:
        raise ValueError('至少需要15张有效图像，建议20～30张不同位置、距离和倾角的图像')
    rms, K, D, rotations, translations = cv2.calibrateCamera(objects, images, size, None, None)
    errors = []
    for obj, img, r, t in zip(objects, images, rotations, translations):
        projected, _ = cv2.projectPoints(obj, r, t, K, D)
        errors.append(np.sqrt(np.mean(np.sum((img.reshape(-1, 2) - projected.reshape(-1, 2))**2, axis=1))))
    if not np.isfinite(rms) or not np.isfinite(K).all() or not np.isfinite(D).all():
        raise ValueError('求解失败：无效参数，请增加拍摄姿态多样性')
    return calibration_data(*size, K, D, rms, errors)


def capture(args, board, dictionary):
    if args.width <= 0 or args.height <= 0 or args.fps <= 0:
        raise ValueError('分辨率和帧率必须为正数')
    device = int(args.device) if args.device.isdecimal() else args.device
    args.capture_dir.mkdir(parents=True, exist_ok=False)
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    try:
        if not cap.isOpened():
            raise RuntimeError('无法打开相机，请关闭占用相机的程序并检查设备路径')
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        cap.set(cv2.CAP_PROP_FPS, args.fps)
        print('固定镜头焦距/对焦；c保存清晰原图，q结束采集并求解。至少15张，建议20～30张。')
        count = 0
        while True:
            ok, image = cap.read()
            if not ok:
                raise RuntimeError('读取相机图像失败')
            if image.shape[1::-1] != (args.width, args.height):
                raise ValueError(f'设备实际输出{image.shape[1::-1]}，与请求分辨率不符')
            points = detect_points(image, board, dictionary)
            preview = image.copy()
            if points:
                for x, y in points[1].reshape(-1, 2):
                    cv2.circle(preview, (int(x), int(y)), 3, (0, 255, 0), -1)
            cv2.putText(preview, f'Saved {count} | c: capture | q: solve', (10, 25), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 0, 255), 2)
            cv2.imshow('Camera calibration', preview)
            key = cv2.waitKey(1) & 0xff
            if key == ord('q'):
                break
            if key == ord('c'):
                if points is None:
                    print('角点不足或共线，未保存')
                else:
                    path = args.capture_dir / f'view_{count:03d}.png'
                    if not cv2.imwrite(str(path), image):
                        raise OSError(f'无法保存{path}')
                    count += 1
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return args.capture_dir


def main():
    p = argparse.ArgumentParser(description='普通相机ChArUco标定，输出ROS CameraInfo格式YAML')
    p.add_argument('--board', default=str(DEFAULT_BOARD))
    p.add_argument('--device', default='/dev/video0')
    p.add_argument('--width', type=int, default=640)
    p.add_argument('--height', type=int, default=480)
    p.add_argument('--fps', type=int, default=30)
    p.add_argument('--capture-dir', type=Path, default=Path('calibration/captures'))
    p.add_argument('--images', type=Path, help='已有原始PNG/JPG图像目录；不打开相机')
    p.add_argument('--output', type=Path, required=True, help='新YAML文件，不覆盖已有结果')
    args = p.parse_args()
    if args.output.exists():
        p.error('输出已存在，请使用新文件名，验证后再切换配置')
    _, board, dictionary = load_board(args.board)
    folder = args.images if args.images else capture(args, board, dictionary)
    objects, images, names = [], [], []
    size = None
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
            continue
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f'无法读取 {path}')
        current_size = image.shape[1::-1]
        if size is not None and current_size != size:
            raise ValueError('图像尺寸混用，请按相机和分辨率分开标定')
        size = current_size
        points = detect_points(image, board, dictionary)
        if points is not None:
            objects.append(points[0]); images.append(points[1]); names.append(path.name)
        else:
            print(f'跳过角点不足图像：{path.name}')
    result = solve_views(objects, images, size)
    result['calibration_quality']['image_files'] = names
    result['calibration_quality']['board'] = yaml.safe_load(Path(args.board).read_text())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as f:
        yaml.safe_dump(result, f, sort_keys=False, allow_unicode=True)
    load_calibration(args.output, *size)
    print(f'已保存 {args.output}；重投影RMS={result["calibration_quality"]["rms_pixels"]:.4f}像素')
    print('结果未自动启用。请检查各帧误差和独立实测距离，再更新camera.calibration_file并重启。')


if __name__ == '__main__':
    main()
