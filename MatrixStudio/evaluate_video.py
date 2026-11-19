"""Extrae un resumen visual y medidas de un MP4 local para comparar ajustes."""
import argparse
import json
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw


def summarize(source, target):
    with av.open(str(source)) as video:
        fps = float(video.streams.video[0].average_rate)
        frames = [frame.to_image() for frame in video.decode(video=0)]
    if not frames:
        raise ValueError('El vídeo no tiene fotogramas decodificables.')
    indices = sorted(set(round(i * (len(frames) - 1) / 5) for i in range(6)))
    width, height = frames[0].size
    sheet = Image.new('RGB', (width * 3, (height + 30) * 2), '#171b16')
    draw = ImageDraw.Draw(sheet)
    for position, index in enumerate(indices):
        x, y = (position % 3) * width, (position // 3) * (height + 30)
        sheet.paste(frames[index], (x, y + 30))
        draw.text((x + 10, y + 8), f'{source.stem} / frame {index}', fill='white')
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target)
    pixels = [np.asarray(frame.resize((128, 128)), dtype=np.float32) for frame in frames]
    differences = [float(np.mean(np.abs(b - a))) for a, b in zip(pixels, pixels[1:])]
    report = {'source': str(source.resolve()), 'frames': len(frames), 'fps': fps, 'duration': len(frames) / fps, 'width': width, 'height': height,
              'sampled_frames': indices, 'mean_frame_difference': float(np.mean(differences)) if differences else 0,
              'note': 'La diferencia entre fotogramas mide cambio, no calidad ni anatomía.'}
    target.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', type=Path)
    parser.add_argument('contact_sheet', type=Path)
    args = parser.parse_args()
    summarize(args.video, args.contact_sheet)
