"""Generate the same board used by calibration as PNG and physical-size SVG."""
import argparse
from pathlib import Path
import cv2
from calibration.board import DEFAULT_BOARD, load_board, board_image
from tools.print_svg import pattern, page


def main():
    p = argparse.ArgumentParser(description='生成ChArUco标定板，SVG按100%实际尺寸打印')
    p.add_argument('--board', default=str(DEFAULT_BOARD))
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    cfg, board, _ = load_board(args.board)
    width = cfg['squares_x'] * cfg['square_length'] * 1000
    height = cfg['squares_y'] * cfg['square_length'] * 1000
    if width > 200 or height > 287:
        p.error('标定板超过A4可打印区域，请减小格子尺寸或另用大幅面打印')
    args.output.mkdir(parents=True, exist_ok=False)
    im = board_image(board, cfg)
    if not cv2.imwrite(str(args.output / 'charuco_board.png'), im):
        raise OSError('无法保存标定板')
    content = pattern(im, (210-width)/2, (297-height)/2, width, height)
    (args.output/'charuco_board_A4.svg').write_text(page(content, 'ChArUco board: print at 100%, do not fit to page'))
    (args.output/'board.yaml').write_text(Path(args.board).read_text())
    print(f'标定板有效区域 {width:g}×{height:g} mm；每格 {cfg["square_length"]*1000:g} mm。打印后用尺复核。')


if __name__ == '__main__':
    main()
