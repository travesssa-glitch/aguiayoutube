# YT Downloader local

Baixa vídeo do YouTube na **máxima qualidade** e o **áudio** (original, MP3, WAV, FLAC).
Roda 100% no seu computador. Use só para conteúdo seu, de domínio público ou com permissão do autor.

## 1. Instalar (uma vez)

1. **Python 3.9+** — https://www.python.org/downloads/ (marque "Add Python to PATH").
2. **ffmpeg** (necessário para juntar vídeo+áudio e converter MP3/WAV/FLAC).
   No **Windows** não precisa fazer nada: na primeira vez o programa baixa sozinho o ffmpeg das releases do
   https://github.com/GyanD/codexffmpeg (versão "essentials") para a pasta `ffmpeg`, ao lado do `server.py`.
   Se o download automático falhar, baixe o `essentials_build.zip` nesse link e coloque `ffmpeg.exe` e `ffprobe.exe` na pasta `ffmpeg`.
   No Mac/Linux: `brew install ffmpeg` ou `sudo apt install ffmpeg`.

## 2. Ligar o servidor

Dê dois cliques em `iniciar.bat` (Windows) ou rode `./iniciar.sh` (Mac/Linux).
Ele instala as dependências, abre a página `http://127.0.0.1:8765` e **precisa ficar aberto** enquanto você baixa.

## 3. Usar na página

Cole o link → ele já procura o vídeo e mostra:
- **Vídeo**: "Máxima qualidade" (automático) ou cada resolução disponível (ex.: 2160p60, 1440p, 1080p...). MKV guarda qualidade máxima; MP4 é mais compatível.
- **Áudio**: Original (sem converter), MP3 320/192/128, WAV, FLAC.
- Ao clicar, abre a janela **Salvar como** para você escolher a pasta.

## 4. Extensão do Chrome

1. Abra `chrome://extensions`, ligue o **Modo do desenvolvedor**.
2. Clique em **Carregar sem compactação** e escolha a pasta `extension`.
3. No YouTube, aparece o botão **⬇ Baixar** no canto da tela em qualquer vídeo. Clique e escolha vídeo ou áudio.
4. O ícone da extensão (barra do Chrome) abre um popup: ele já pega o link da aba atual ou o último link que você copiou.
5. Ao terminar o preparo, o Chrome abre a janela para escolher onde salvar.
   Se quiser que o Chrome sempre pergunte, em `chrome://settings/downloads` ligue "Perguntar onde salvar cada arquivo".

## Dicas e problemas

- **"Servidor local desligado"**: abra o `iniciar.bat`.
- **Parou de funcionar / erro 403**: o YouTube muda sempre. Atualize: `python -m pip install -U yt-dlp` (o `iniciar.bat` já faz isso).
- **Sobre WAV**: o YouTube só guarda áudio com perdas (Opus ~160 kbps, AAC até ~256 kbps). WAV e FLAC guardam o mesmo som sem comprimir de novo, mas não ficam melhores que o original. Para a máxima qualidade real, use "Original" ou FLAC.
- **Sobre MP4**: em 4K o YouTube usa VP9/AV1; no MP4 alguns players antigos podem não abrir. Use MKV ou o VLC.
- Vídeos privados, de membros ou com restrição de idade podem não baixar.
- Arquivos temporários ficam na pasta temporária do sistema e são apagados depois de 1 hora.
