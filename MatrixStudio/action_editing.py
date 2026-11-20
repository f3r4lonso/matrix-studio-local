"""Join two generated continuations and retime their original frames explicitly."""
import io
from fractions import Fraction
import av


def join_action_segments(first, second, params):
    """Two N-frame takes share a boundary; export 2N-1 originals at twice base FPS."""
    multiplier = params.get('interpolation', 1)
    base_fps, count = params['fps'], params['frames']
    if multiplier not in (1, 2) or base_fps not in (16, 24) or count not in (81, 121):
        raise ValueError('La edición necesita dos clips completos de cinco segundos.')
    takes = []
    for content in (first, second):
        with av.open(io.BytesIO(content)) as container:
            stream = container.streams.video[0]
            frames = [frame.to_ndarray(format='rgb24') for frame in container.decode(video=0)]
            if float(stream.average_rate) != base_fps * multiplier:
                raise ValueError('Los FPS de la escena no coinciden con la receta.')
        expected = (count - 1) * multiplier + 1
        if len(frames) != expected:
            raise ValueError('La escena no contiene todos los fotogramas esperados.')
        originals = frames[::multiplier]
        if any(frame.shape != (params['height'], params['width'], 3) for frame in originals):
            raise ValueError('Las resoluciones de las escenas deben coincidir.')
        takes.append(originals)
    combined = takes[0] + takes[1][1:]
    fps = base_fps * 2
    if len(combined) / fps < 5:
        raise ValueError('El resultado debe durar al menos cinco segundos reales.')
    output = io.BytesIO()
    with av.open(output, mode='w', format='mp4') as container:
        stream = container.add_stream('libx264', rate=fps)
        stream.width, stream.height, stream.pix_fmt = params['width'], params['height'], 'yuv420p'
        stream.options = {'crf': '18', 'preset': 'medium'}
        for index, pixels in enumerate(combined):
            frame = av.VideoFrame.from_ndarray(pixels, format='rgb24')
            frame.pts, frame.time_base = index, Fraction(1, fps)
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return output.getvalue()
