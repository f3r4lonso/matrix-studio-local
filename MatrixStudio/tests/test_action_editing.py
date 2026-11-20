import io
import sys
import unittest
from pathlib import Path
import av
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from action_editing import join_action_segments


def take(count, fps, blue):
    output = io.BytesIO()
    with av.open(output, 'w', format='mp4') as container:
        stream = container.add_stream('libx264', rate=fps)
        stream.width = stream.height = 64
        stream.pix_fmt = 'yuv420p'
        for index in range(count):
            pixels = np.full((64, 64, 3), (index % 200, 40, blue), dtype=np.uint8)
            for packet in stream.encode(av.VideoFrame.from_ndarray(pixels, format='rgb24')):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return output.getvalue()


class ActionEditingTest(unittest.TestCase):
    def test_retimed_continuations_have_real_duration_and_both_takes(self):
        for base_count, base_fps, multiplier in [(81, 16, 2), (121, 24, 1)]:
            count = (base_count - 1) * multiplier + 1
            first, second = take(count, base_fps*multiplier, 20), take(count, base_fps*multiplier, 220)
            result = join_action_segments(first, second, dict(frames=base_count, fps=base_fps,
                interpolation=multiplier, width=64, height=64))
            with av.open(io.BytesIO(result)) as container:
                fps = float(container.streams.video[0].average_rate)
                frames = list(container.decode(video=0))
            self.assertEqual(len(frames), base_count*2-1)
            self.assertEqual(fps, base_fps*2)
            self.assertGreaterEqual(len(frames)/fps, 5)
            self.assertLess(frames[base_count-1].to_ndarray(format='rgb24')[:,:,2].mean(), 40)
            self.assertGreater(frames[base_count].to_ndarray(format='rgb24')[:,:,2].mean(), 200)
            times = [float(f.pts*f.time_base) for f in frames]
            self.assertTrue(all(a < b for a,b in zip(times,times[1:])))

    def test_incomplete_or_mismatched_takes_are_rejected(self):
        params = dict(frames=81, fps=16, interpolation=2, width=64, height=64)
        for count, fps in [(160,32), (161,16)]:
            content = take(count, fps, 20)
            with self.assertRaises(ValueError):
                join_action_segments(content, content, params)
