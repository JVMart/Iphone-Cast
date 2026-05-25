# Iphone-Cast

> Lee esto en [English](README.md).

App de escritorio Windows para **duplicar la pantalla del iPhone** (AirPlay 2 Mirroring) al PC. Pensada para uso personal.

Esta carpeta contiene un **launcher Python** sencillo (GUI Tkinter) que controla **UxPlay**, el receptor AirPlay 2 open source que hace el trabajo real (handshake criptografico, recepcion del stream H.264, render con GStreamer).

```
+----------+    AirPlay 2 mirror     +----------------------+
|  iPhone  | ----------------------> |  PC Windows          |
|          |                         |  +----------------+  |
| Centro   |                         |  | Iphone-Cast.py |  |
| Control  |  Centro de Control ->   |  | (GUI/launcher) |  |
|   ->     |  Duplicar pantalla ->   |  +-------+--------+  |
| Duplicar |  "PC-Cast"              |          v           |
| pantalla |                         |       uxplay.exe     |
+----------+                         |       (GStreamer)    |
                                     +----------------------+
```

## Requisitos

- **Windows 10/11** (64-bit)
- **Python 3.10+** instalado y en el PATH
- iPhone y PC en la **misma red WiFi** (no VPN, no red de invitados)

Todo lo demas (MSYS2, GStreamer, UxPlay, Bonjour SDK, venv, `.exe`, acceso directo, reglas de firewall) lo monta `install.ps1`.

## Instalacion rapida

```powershell
git clone https://github.com/JVMart/Iphone-Cast.git
cd Iphone-Cast
.\install.ps1
```

En un Windows 10/11 limpio tarda **25-40 minutos** sin asistencia. Cada paso es idempotente, asi que si algo falla a mitad puedes volverlo a ejecutar sin miedo: salta lo que ya este hecho.

| Flag                 | Efecto                                                            |
|----------------------|-------------------------------------------------------------------|
| `-SkipFirewall`      | No toca las reglas de firewall (las pones tu a mano).             |
| `-Force`             | Re-hace todos los pasos (util tras actualizar UxPlay o GStreamer).|

Si PowerShell bloquea el script por politica de ejecucion:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

> **Que hace `install.ps1`:** (1) descarga e instala MSYS2 silenciosamente, (2) lanza `scripts\build_uxplay.sh` que instala 244 paquetes de pacman + clona el SDK de Bonjour + compila UxPlay con Ninja, (3) crea `.venv\`, (4) compila `Iphone-Cast.exe` con el icono incrustado, (5) pone el acceso directo en el escritorio, (6) anade 3 reglas de firewall (pide elevacion). Lee el script para detalles.

## Instalacion manual (avanzada)

Si prefieres entender o controlar cada paso, o si `install.ps1` falla y quieres depurar, sigue las secciones de abajo. Es lo mismo que hace el script.

### Instalar UxPlay en Windows

UxPlay no tiene un instalador `.msi` oficial. Se instala via **MSYS2** (un entorno tipo Linux para Windows que trae GStreamer). Es tedioso la primera vez pero solo se hace una.

#### Paso 1 - Instalar MSYS2

Descarga e instala MSYS2 desde https://www.msys2.org/ . Acepta la ruta por defecto `C:\msys64`.

Al terminar abrira una terminal **MSYS2 UCRT64**. Si no, abrela desde el menu Inicio: **"MSYS2 UCRT64"** (importante, no la "MSYS2 MSYS").

#### Paso 2 - Actualizar MSYS2

En la terminal UCRT64:

```bash
pacman -Syu
# Cierra y vuelve a abrir UCRT64 cuando lo pida.
pacman -Su
```

#### Paso 3 - Instalar dependencias y compilar UxPlay

**3a. Paquetes pacman.** En la terminal UCRT64:

```bash
pacman -S --needed \
    git \
    mingw-w64-ucrt-x86_64-cmake \
    mingw-w64-ucrt-x86_64-ninja \
    mingw-w64-ucrt-x86_64-gcc \
    mingw-w64-ucrt-x86_64-openssl \
    mingw-w64-ucrt-x86_64-libplist \
    mingw-w64-ucrt-x86_64-gstreamer \
    mingw-w64-ucrt-x86_64-gst-plugins-base \
    mingw-w64-ucrt-x86_64-gst-plugins-good \
    mingw-w64-ucrt-x86_64-gst-plugins-bad \
    mingw-w64-ucrt-x86_64-gst-plugins-ugly \
    mingw-w64-ucrt-x86_64-gst-libav
```

**3b. Bonjour SDK.** UxPlay necesita los headers de Apple Bonjour (`dns_sd.h`, `dnssd.lib`) para anunciar el servicio mDNS en la red. No esta en pacman. La forma rapida es clonar un mirror del SDK ya extraido:

```bash
git clone --depth 1 https://github.com/G-P-S/bonjour-win-sdk.git /c/BonjourSDK
export BONJOUR_SDK_HOME="C:\\BonjourSDK"
```

Si quieres que sea permanente, anade esa linea `export` a `~/.bashrc`.

> Alternativa: descarga "Bonjour SDK for Windows v3.0" del sitio oficial de Apple (developer.apple.com, requiere cuenta gratuita) e instalalo. Por defecto queda en `C:\Program Files\Bonjour SDK`, que es donde UxPlay lo busca sin necesidad de tocar `BONJOUR_SDK_HOME`.

**3c. Clonar y compilar UxPlay.**

```bash
git clone https://github.com/FDH2/UxPlay.git
cd UxPlay
mkdir build && cd build
cmake .. -G Ninja -DCMAKE_INSTALL_PREFIX=/ucrt64
ninja
ninja install
```

Esto deja `uxplay.exe` en `C:\msys64\ucrt64\bin\uxplay.exe` (esta ruta la detecta la app automaticamente, y es la misma carpeta donde estan las DLLs de GStreamer).

> **Nota:** las guias antiguas usaban `cmake -G "MinGW Makefiles"` + `mingw32-make`. El paquete actual de `mingw-w64-ucrt-x86_64-gcc` ya no incluye `mingw32-make.exe`, asi que usamos Ninja.

> **Atajo:** algunos releases de UxPlay incluyen binarios precompilados en la pestana Releases del repositorio. Si encuentras uno para Windows, descargalo y pon la ruta en `config.py -> UXPLAY_PATH`. Te ahorras todo lo anterior.

#### Paso 4 - Verifica desde una terminal normal de Windows

Abre **cmd** o **PowerShell** y prueba:

```cmd
C:\msys64\ucrt64\bin\uxplay.exe -h
```

Si imprime la ayuda, esta instalado. Si dice que falta una DLL de GStreamer, anade `C:\msys64\ucrt64\bin` al PATH del sistema (Configuracion -> Sistema -> Acerca de -> Configuracion avanzada del sistema -> Variables de entorno).

### Crear venv de Python

```powershell
python -m venv .venv
.\.venv\Scripts\activate
# Esta app solo usa libreria estandar, no hace falta pip install nada.
```

## Uso

Doble click en **`Iphone-Cast.exe`** (junto a `main.py`). Equivalente a abrir una terminal y ejecutar:

```powershell
python main.py
```

> El `.exe` es un wrapper Win32 minimo (~520 KB con el icono incrustado) que arranca `pythonw.exe main.py` sin consola. Prefiere el `.venv` del proyecto si existe; si no, cae al `pythonw.exe` del PATH. Para reconstruirlo despues de tocar `launcher.c`, `launcher.rc` o el icono:
>
> ```bash
> # en la terminal MSYS2 UCRT64, desde el directorio del proyecto
> /ucrt64/bin/magick.exe -background none -density 512 icon.svg \
>     -define icon:auto-resize="256,128,64,48,32,16" Iphone-Cast.ico
> /ucrt64/bin/windres.exe launcher.rc -O coff -o launcher_res.o
> /ucrt64/bin/gcc.exe -O2 -mwindows -static -static-libgcc \
>     -o Iphone-Cast.exe launcher.c launcher_res.o
> ```
>
> En el escritorio se crea tambien un acceso directo (`Iphone-Cast.lnk`) con el mismo icono apuntando al `.exe`.

1. Pulsa **Iniciar receptor** en la app.
2. En el iPhone: desliza desde la esquina superior derecha para abrir **Centro de Control**.
3. Pulsa **Duplicar pantalla** (icono de dos rectangulos solapados).
4. Selecciona **PC-Cast** de la lista.
5. La pantalla del iPhone aparecera en una ventana del PC. Abre tu app de peliculas y reproduce.
6. (Opcional) Pulsa **Pantalla completa** para ver solo el mirror, sin bordes ni decoraciones. Aparece un boton flotante `[X Salir]` arriba a la derecha que se desvanece tras 3 segundos sin actividad de raton/teclado. Pulsa **Esc** o el boton flotante para salir.
7. Para terminar: en el iPhone, vuelve a Centro de Control -> Duplicar pantalla -> **Detener duplicacion**. Luego pulsa **Parar** en el PC.

Mientras el iPhone esta duplicando, el monitor del PC se mantiene despierto (`SetThreadExecutionState`) para que Windows no atenue ni apague la pantalla a mitad de una pelicula. El bloqueo se libera automaticamente al desconectar el iPhone o pulsar **Parar**.

## Configuracion (`config.py`)

| Variable             | Para que sirve                                                 |
|----------------------|----------------------------------------------------------------|
| `SERVICE_NAME`       | Nombre que ves en el iPhone (por defecto "PC-Cast").           |
| `UXPLAY_PATH`        | Ruta absoluta a uxplay.exe si la autodeteccion falla.          |
| `START_FULLSCREEN`   | Si True, UxPlay arranca en pantalla completa (`-fs`).          |
| `UXPLAY_EXTRA_ARGS`  | Lista de flags extra (ver `uxplay -h` para todos).             |

Flags utiles para `UXPLAY_EXTRA_ARGS`:

- `["-vs", "d3d11videosink"]` - fuerza el sink Direct3D 11 (mas rapido en Windows).
- `["-fps", "60"]` - fuerza 60fps (si tu iPhone lo soporta).
- `["-p", "tcp"]` - usa TCP en vez de UDP (estabiliza en WiFi con interferencias).
- `["-async"]` - modo audio asincrono (latencia un poco mayor, menos cortes).

## Firewall y red

La primera vez Windows preguntara si quieres permitir `uxplay.exe` (y tal vez Python). **Permite ambos en red privada.**

Si no aparece "PC-Cast" en el iPhone:

```powershell
# PowerShell como administrador
New-NetFirewallRule -DisplayName "UxPlay AirPlay TCP" `
    -Direction Inbound -Protocol TCP -LocalPort 7000,7001,7100 -Action Allow
New-NetFirewallRule -DisplayName "UxPlay AirPlay UDP" `
    -Direction Inbound -Protocol UDP -LocalPort 6000-7100 -Action Allow
New-NetFirewallRule -DisplayName "mDNS" `
    -Direction Inbound -Protocol UDP -LocalPort 5353 -Action Allow
```

## Apps que funcionan y las que no

**Funcionan bien** (sin DRM o con DRM permisivo): Fotos, Camara, Safari (web), YouTube, Twitch, juegos, escritorio del iPhone, mensajes, apps "alternativas" de streaming, navegacion general.

**NO funcionan** (bloquean por DRM): **Netflix, Disney+, HBO Max, Apple TV+, Prime Video, Movistar+, DAZN, Filmin**. Estas apps detectan que el receptor no es MFi-certificado y **pintaran la pantalla en negro o mostraran un error**. No hay forma legal de saltarse esto desde el receptor - es DRM end-to-end.

Si tu "app de peliculas" es una de las anteriores, **no podras castearla por mirroring**. Esto es independiente de UxPlay: ninguna solucion (ni de pago) que no este en la lista MFi de Apple lo permitira.

## Estructura del proyecto

```
Iphone-cast/
|-- install.ps1         # Instalador todo-en-uno (entrada principal)
|-- scripts/
|   +-- build_uxplay.sh # Compilacion de UxPlay (lo invoca install.ps1)
|-- main.py             # GUI Tkinter (launcher)
|-- uxplay_runner.py    # Wrapper subprocess de uxplay.exe
|-- fullscreen.py       # Pantalla completa Win32, overlay, hook Esc, keep-awake
|-- config.py           # Nombre del servicio, ruta a UxPlay, flags extra
|-- launcher.c          # Fuente del wrapper .exe (Win32, compilable con gcc)
|-- launcher.rc         # Recurso que incrusta el icono en el .exe
|-- icon.svg            # Diseno vectorial del icono (estilo AirPlay)
|-- PRIVACY.md          # Politica de privacidad (para Microsoft Partner Center)
|-- README.md           # README en ingles (por defecto)
+-- README.es.md        # Este archivo
```

`Iphone-Cast.exe`, `Iphone-Cast.ico`, `.venv/` y `launcher_res.o` son artefactos que genera `install.ps1`; estan en `.gitignore` para no contaminar el repo publico.

## Troubleshooting

- **"No se encontro uxplay.exe"** -> instala UxPlay (seccion de arriba) o pon `UXPLAY_PATH` en `config.py`.
- **Aparece "PC-Cast" pero al pulsar no conecta** -> puerto 7000 ocupado por otra app (cierra AirServer/5KPlayer/iTunes). O firewall bloqueando UDP 6000-7100.
- **Conecta pero la imagen esta negra** -> la app del iPhone tiene DRM. No hay solucion.
- **Imagen entrecortada / audio que se desincroniza** -> prueba `UXPLAY_EXTRA_ARGS = ["-p", "tcp"]` o acerca el iPhone al router.
- **Ventana de UxPlay no aparece** -> el sink de GStreamer puede haber fallado. Prueba `UXPLAY_EXTRA_ARGS = ["-vs", "d3d11videosink"]` o `["-vs", "glimagesink"]`.
