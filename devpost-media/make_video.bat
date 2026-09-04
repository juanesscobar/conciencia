@echo off
REM Ensambla conciencia-demo.mp4 desde las slides (fade-in por segmento + concat)
cd /d C:\Users\juane\.openclaw\workspace\mission-control\devpost-media

ffmpeg -y -loop 1 -t 4 -i s-title.png -vf "fade=t=in:st=0:d=0.6,format=yuv420p" -c:v libx264 -preset medium -r 25 seg01.mp4
ffmpeg -y -loop 1 -t 5 -i s-app-clean.png -vf "fade=t=in:st=0:d=0.5,format=yuv420p" -c:v libx264 -preset medium -r 25 seg02.mp4
ffmpeg -y -loop 1 -t 5 -i s-form-filled.png -vf "fade=t=in:st=0:d=0.5,format=yuv420p" -c:v libx264 -preset medium -r 25 seg03.mp4
ffmpeg -y -loop 1 -t 5 -i s-submitted.png -vf "fade=t=in:st=0:d=0.5,format=yuv420p" -c:v libx264 -preset medium -r 25 seg04.mp4
ffmpeg -y -loop 1 -t 5 -i s-counter.png -vf "fade=t=in:st=0:d=0.5,format=yuv420p" -c:v libx264 -preset medium -r 25 seg05.mp4
ffmpeg -y -loop 1 -t 5 -i s-agent.png -vf "fade=t=in:st=0:d=0.5,format=yuv420p" -c:v libx264 -preset medium -r 25 seg06.mp4
ffmpeg -y -loop 1 -t 9 -i s-cli-run.png -vf "fade=t=in:st=0:d=0.5,format=yuv420p" -c:v libx264 -preset medium -r 25 seg07.mp4
ffmpeg -y -loop 1 -t 8 -i s-cli-signal.png -vf "fade=t=in:st=0:d=0.5,format=yuv420p" -c:v libx264 -preset medium -r 25 seg08.mp4
ffmpeg -y -loop 1 -t 7 -i s-cli-eco.png -vf "fade=t=in:st=0:d=0.5,format=yuv420p" -c:v libx264 -preset medium -r 25 seg09.mp4
ffmpeg -y -loop 1 -t 5 -i s-close.png -vf "fade=t=in:st=0:d=0.6,format=yuv420p" -c:v libx264 -preset medium -r 25 seg10.mp4

(for %%f in (seg01 seg02 seg03 seg04 seg05 seg06 seg07 seg08 seg09 seg10) do @echo file '%%f.mp4') > list.txt
ffmpeg -y -f concat -safe 0 -i list.txt -c copy conciencia-demo.mp4

REM pista de audio silenciosa (YouTube la acepta; el usuario puede narrar después)
ffmpeg -y -i conciencia-demo.mp4 -f lavfi -t 58 -i anullsrc=r=44100:cl=stereo -shortest -c:v copy -c:a aac conciencia-demo-final.mp4
move /y conciencia-demo-final.mp4 conciencia-demo.mp4 >nul

for %%f in (seg*.mp4 list.txt) do del %%f
echo DONE
