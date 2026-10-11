"""Compose narrated dashboard screenshots into a downloadable H.264 MP4."""
import json
import subprocess
import textwrap
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SCENES = json.loads((ROOT / 'scenes.json').read_text())

def run(args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

if __name__ == '__main__':
    import sys
    if '--narrate' in sys.argv:
        for i, scene in enumerate(SCENES):
            text = ASSETS / f'narration_{i}.txt'
            text.write_text(scene['narration'])
            run(['say','-v','Samantha','-r','145','-f',str(text),'-o',str(ASSETS/f'voice_{i}.aiff')])
        print('Narration generated.')
        sys.exit()
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',24)
    bold = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',28)
    timings = []
    elapsed = 0
    subtitles = []
    transcript = ['Singapore Haze Observatory — narrated walkthrough\n']
    def stamp(t):
        ms = round(t*1000)
        return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
    for i, scene in enumerate(SCENES):
        wav = ASSETS/f'voice_{i}.wav'
        run([FFMPEG,'-y','-i',str(ASSETS/f'voice_{i}.aiff'),str(wav)])
        with wave.open(str(wav)) as audio:
            seconds = audio.getnframes()/audio.getframerate()
        if seconds < 2:
            raise ValueError('Narration is empty or too short')
        duration = max(19, seconds+1.0)
        timings.append(duration)
        canvas = Image.new('RGB',(1600,1120),'#123c43')
        screenshot = Image.open(ASSETS/f'{scene["image"]}.png').convert('RGB')
        canvas.paste(screenshot,(0,64))
        draw = ImageDraw.Draw(canvas)
        draw.text((28,16),scene['title'],font=bold,fill='white')
        draw.text((28,1080),scene['summary'],font=font,fill='white')
        frame = ASSETS/f'frame_{i}.png'
        canvas.save(frame)
        segment = ASSETS/f'segment_{i}.mp4'
        run([FFMPEG,'-y','-loop','1','-framerate','24','-i',str(frame),'-i',str(wav),
             '-t',str(duration),'-vf','scale=1600:1120,format=yuv420p',
             '-af','apad','-c:v','libx264','-preset','fast','-crf','22',
             '-c:a','aac','-b:a','128k','-ar','48000',str(segment)])
        # Sentence captions form a separate subtitle track, suitable for players.
        sentences = scene['narration'].split('. ')
        counts = [len(s.split()) for s in sentences]
        cursor = elapsed
        for sentence,count in zip(sentences,counts):
            end = cursor + seconds*count/sum(counts)
            subtitles.append(f'{len(subtitles)+1}\n{stamp(cursor)} --> {stamp(end)}\n'+ '\n'.join(textwrap.wrap(sentence.rstrip('.')+'.',85))+'\n')
            cursor = end
        transcript.append(f'{stamp(elapsed)[:-4]}  {scene["title"]}\n{scene["narration"]}\n')
        elapsed += duration
        print(f'Scene {i+1}: {duration:.1f}s',flush=True)
    listing = ASSETS/'segments.txt'
    listing.write_text('\n'.join(f"file '{ASSETS/f'segment_{i}.mp4'}'" for i in range(len(SCENES))))
    captions = ROOT/'walkthrough.srt'
    captions.write_text('\n'.join(subtitles))
    (ROOT/'transcript.txt').write_text('\n'.join(transcript))
    run([FFMPEG,'-y','-f','concat','-safe','0','-i',str(listing),'-i',str(captions),
         '-map','0:v','-map','0:a','-map','1:0','-c:v','copy','-c:a','copy','-c:s','mov_text',
         '-metadata:s:s:0','language=eng','-metadata','title=Singapore Haze Observatory Walkthrough',
         '-movflags','+faststart',str(ROOT/'singapore_haze_walkthrough.mp4')])
    print(f'Finished: {elapsed:.1f} seconds')
