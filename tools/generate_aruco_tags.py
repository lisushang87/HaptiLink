"""Generate the configured prism markers; never initialize camera hardware."""
import argparse
from pathlib import Path
import cv2
import numpy as np
from tracking.config import DEFAULT_CONFIG, load_config
from tools.print_svg import pattern, page


def main():
    parser = argparse.ArgumentParser(description='按跟踪配置生成两组六棱柱标签')
    parser.add_argument('--config', default=str(DEFAULT_CONFIG))
    parser.add_argument('--output', type=Path, required=True, help='输出到新目录，避免覆盖已有标签')
    parser.add_argument('--size', type=int, default=300, help='包含白边的图像边长（像素）')
    args = parser.parse_args()
    config = load_config(args.config)
    cfg = config['tags']
    if args.size < 40:
        parser.error('--size 必须至少为40像素')
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, cfg['dictionary']))
    generate = getattr(cv2.aruco, 'generateImageMarker', None) or cv2.aruco.drawMarker
    black_mm = cfg['hexagon_tag_black_size'] * 1000
    cut_mm = config['hexagon']['hexagon_size'] * 1000
    if not black_mm < cut_mm <= 70:
        parser.error('裁剪框（hexagon.hexagon_size）必须大于标签黑边尺寸且不超过70mm，以保留白边并适配A4排版')
    tag_pixels = round(args.size * black_mm / cut_mm)
    margin = (args.size - tag_pixels) // 2
    if margin < 1 or tag_pixels < dictionary.markerSize + 2:
        parser.error('--size过小，无法保留标签细节和白边')
    args.output.mkdir(parents=True, exist_ok=False)
    sheets = [[], []]
    for index, mid in enumerate(cfg['hexagon_1_ids'] + cfg['hexagon_2_ids']):
        image = np.full((args.size, args.size), 255, np.uint8)
        image[margin:margin+tag_pixels, margin:margin+tag_pixels] = generate(dictionary, mid, tag_pixels)
        # Six centered tags with separate physical-size cutting guides.
        sheet, slot = divmod(index, 6)
        x = 57.5 + (slot % 2) * 95 - black_mm / 2
        y = 60 + (slot // 2) * 85 - black_mm / 2
        cells = generate(dictionary, mid, dictionary.markerSize + 2)
        sheets[sheet].append(pattern(cells, x, y, black_mm, black_mm))
        cut_x, cut_y = x - (cut_mm-black_mm)/2, y - (cut_mm-black_mm)/2
        sheets[sheet].append(f'<rect class="cut-guide" x="{cut_x}" y="{cut_y}" width="{cut_mm}" height="{cut_mm}" fill="none" stroke="#888888" stroke-width="0.15" stroke-dasharray="2 1"/>')
        sheets[sheet].append(f'<text x="{cut_x}" y="{cut_y+cut_mm+5}" font-size="3">ID {mid} | black {black_mm:g} mm | cut {cut_mm:g} mm</text>')
        path = args.output / f'aruco_id_{mid}.png'
        if not cv2.imwrite(str(path), image):
            raise OSError(f'无法保存 {path}')
    for index, content in enumerate(sheets, 1):
        content.insert(0, f'<text x="10" y="12" font-size="4">Hand {index} | {cfg["dictionary"]} | print 100%, no scaling</text>')
        (args.output / f'hand_{index}_A4.svg').write_text(page(''.join(content), f'Hand {index} markers'))
    (args.output / 'PRINT.txt').write_text(f'优先打印SVG：A4纸、100%/实际大小，关闭适应页面及页眉页脚。每个灰色虚线裁剪框为{cut_mm:g}×{cut_mm:g}毫米（取自hexagon.hexagon_size），沿虚线剪下。黑色区域边长必须为{black_mm:g}毫米，不含白边；四周白边各{(cut_mm-black_mm)/2:g}毫米，请保留。打印后用尺复核；按配置列表顺序贴六个侧面，方向一致。PNG没有可靠物理尺寸，请勿直接按默认缩放打印。\n')
    print(f"已生成12张 {cfg['dictionary']} 标签到 {args.output}")
    print(f"裁剪框边长 {cut_mm:g} mm，四周白边各 {(cut_mm-black_mm)/2:g} mm。")
    print(f"打印后黑色区域边长应为 {cfg['hexagon_tag_black_size']} 米（不含白边）。")


if __name__ == '__main__':
    main()
