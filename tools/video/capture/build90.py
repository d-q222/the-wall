import subprocess, textwrap, glob
raw = glob.glob('raw2/*.webm')[0]
lines = open('lines.txt').read().strip().split('\n')
starts = [1.345, None, 12.16, 20.07, 35.89, 49.71, 63.53]
ends = [12.16, None, 20.07, 35.89, 49.71, 63.53, 73.5]
F = '/System/Library/Fonts/Supplemental/Arial.ttf'
def dur(f): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f]))
parts = []
for i in range(7):
    n = f'n{i+1}.aiff'; d = round(dur(n) + 3.0, 2)
    open(f'cap{i+1}.txt','w').write(textwrap.fill(lines[i], 58))
    cap0 = f"drawtext=fontfile={F}:textfile=cap{i+1}.txt:fontsize=44:fontcolor=white:line_spacing=10:box=1:boxcolor=black@0.7:boxborderw=20:x=(w-text_w)/2:y=h-text_h-70"
    if starts[i] is None:
        open('title.txt','w').write('So their AI has to forget everything.')
        src = ['-loop','1','-framerate','30','-t',str(d),'-i','title.png']
        vf = "scale=1920:1080,fps=30"
    else:
        src = ['-ss',str(starts[i]),'-t',str(min(d, ends[i]-starts[i]-1.6)),'-i',raw]
        vf = f"scale=1920:1080,fps=30,tpad=stop_mode=clone:stop_duration={d}"
    out = f'scene{i+1}.mp4'
    subprocess.check_call(['ffmpeg','-y','-v','error',*src,'-itsoffset','0.5','-i',n,'-i',f'cap{i+1}.png','-filter_complex',f'[0:v]{vf}[b];[b][2:v]overlay=0:0[v];[1:a]apad,aresample=48000[a]','-map','[v]','-map','[a]','-t',str(d),'-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p','-r','30','-c:a','aac','-ar','48000','-ac','2',out])
    parts.append(out)
open('list.txt','w').write(''.join(f"file '{p}'\n" for p in parts))
subprocess.check_call(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i','list.txt','-c','copy','../wall-demo-90s.mp4'])
