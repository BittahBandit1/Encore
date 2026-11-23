# Player guide

Everything you need to play the Persona Dancing games with Encore: what to bring, how to install it, the first run,
the controls and settings, and what to do when something goes wrong.

## What you need

- **A computer:** a Mac with Apple silicon (any M-series) on macOS 11 Big Sur or newer, a Windows 10 or 11 PC on x86-64,
  or a Linux PC on x86-64, including a Steam Deck.
- **Your own copies of the games**, with their updates if you have them. Encore takes game folders copied from your
  Vita, PKG files, or a whole folder to search. See the [supported games](../README.md) for exactly which releases play.
- **Their licences.** A game folder copied from your Vita carries its own. For PKGs, Encore fetches the licence from
  your Vita over Wi-Fi, once.
- **The PS Vita system software update file**, free from Sony's website. Encore uses the system libraries inside it and
  builds every game against them.

Nothing you add leaves your computer, and Encore itself contains no Sony or game code.

## Installing

There's no Encore release yet: until there is, build it from source as the [README](../README.md#building-from-source)
describes. Once releases are out, installing works like this.

**On a Mac**

1. Open the `.dmg` and drag **Encore** into Applications.
2. Open it from Applications. macOS asks once whether to open an app downloaded from the internet: choose **Open**.
3. If your Mac doesn't have Apple's free Command Line Tools, Encore asks you to install them. It uses them to build each
   game on your Mac. Install them from the window that opens, then open Encore again.

**On Windows**

1. Unzip the download anywhere you like, outside `Program Files`.
2. Double-click **Encore.exe**. Encore isn't signed yet, so Windows may say it protected your PC: choose **More info**,
   then **Run anyway**. You only do this once per download.

**On Linux and Steam Deck**

1. Put the `.AppImage` anywhere you like and allow it to run as a program: in the file manager, its Properties ›
   Permissions (or `chmod +x` on it).
2. Open it. On a Steam Deck, in Desktop Mode, add it to Steam as a non-Steam game, then start it from Game Mode.

Encore keeps your games, builds and saves in its library, a folder apart from the install, so replacing the install
never touches them: `~/Library/Application Support/ProjectNativ/Nativ/library` on a Mac,
`%LOCALAPPDATA%\ProjectNativ\Nativ\library` on Windows and `~/.local/share/ProjectNativ/Nativ/library` on Linux. (The
folder keeps Project Nativ's name, which Encore is built on.)

**Updating:** when a new version is out, the launcher says so above your library, with a link to its download page. On
a Mac, drag the new Encore into Applications and replace the old one; on Windows, replace the `Encore` folder with the
new one; on Linux, the `.AppImage` with the new one. Your library stays where it is. Each game rebuilds once with the
new version the next time you play it.

## The first run

After a welcome screen, the launcher walks you through a few steps. You can come back to them any time through
**Setup**, at the top right.

1. **Firmware.** Download the PS Vita system software update file (`PSVUPDAT.PUP` or `PSP2UPDAT.PUP`, version 3.74; any
   recent version works) from Sony's page, which the launcher links to, then choose the file. Encore decrypts it once.
2. **Games.** Add your games and their updates. Each one is decrypted and checked against its game pack, which knows
   which versions it plays. Licences are kept once, so later updates and DLC for the same game just add.
3. **Online name.** The Persona Dancing games don't play online, so this step doesn't matter for Encore.
4. **Done.** Your library opens.

## Building and playing

The first time you play a game, Encore builds it into a native program on your computer. That takes a few minutes, and
after that it starts straight away.

After you update Encore, the next Play brings that game's build up to date before it starts. That's usually under a
minute; when an update changes how games are translated, it's as long as the first build.

The first time you start a game, Encore may pause it on a "Preparing shaders" card while it builds the game's shaders
for your GPU. You can skip it and play at once: the shaders keep building while you play, with short pauses until
they're done. Later starts are quick. The card comes back only when there's something new to build, such as after an
update.

## Controls

| Vita | Keyboard and mouse | Gamepad |
|---|---|---|
| D-pad | Arrow keys | D-pad |
| Cross, Circle, Square, Triangle | Space, C, F, E | Cross, Circle, Square, Triangle (Xbox: A, B, X, Y) |
| Start, Select | Enter, Tab | Options, Share or Create (Xbox: Menu, View) |
| L, R | Right and left mouse buttons (or Q and R) | L2, R2 (Xbox: LT, RT) |
| Sticks | WASD, and the mouse | Sticks |
| Front touch panel | Hold Alt (Option on a Mac) and click or drag. Where the mouse doesn't aim, a plain click works too. | The touchpad, or hold L1 and steer a cursor with a stick, touching with Cross |
| Rear touch panel | Right mouse button, the same way | The touchpad with R1 held, or hold R1 and use a stick and Cross |

On a touchscreen, touch the picture: that's the front panel. Hold R1 as a finger lands for the rear panel.

Buttons are named as on a PlayStation controller; on an Xbox controller, L1 and R1 are LB and RB, and Cross is A.

**L and R buttons** (Controls, in the menu and the launcher's Settings) swaps the shoulder pairs: L and R on the
bumpers (L1 and R1), and the touch cursor on the triggers.

The first time you start a game, a card shows how to touch the screen with a keyboard and mouse, a controller or a
touch screen, with the one you're using highlighted. Touch once the way it shows to carry on (Esc skips it). It appears
only once.

**Keys while playing:**

- **F10**, or the PS button: the in-game menu, with display, controls and frame rate. The game pauses while it's open.
- **F1**: the frame-rate overlay.
- **F2**: cycle the render scale (sharper picture, more GPU work).
- **F5**: mark a moment for a bug report (see below).
- **F12**: capture a frame's graphics, for graphics bugs.

Closing the game's window (Cmd+W or Cmd+Q on a Mac, Alt+F4 elsewhere, or its close button) asks first, so a stray
shortcut doesn't lose your progress: **Keep playing** or **Quit**, and closing it again quits.

## Settings

**Settings**, at the top right of the launcher, holds the display, controls and sound for every game. Each game's card
has a menu with that game's own options. Some worth knowing:

- **Render scale**: draws the game at up to six times the Vita's resolution.
- **Aspect ratio**: native, 21:9, 32:9 or your window's shape. The HUD keeps its own shape on wide screens.
- **Frame rate**: 30 or 60. In the Persona Dancing games the dances keep time with the music at 60.
- **Texture pack**: a Vita3K texture pack for the game, used as it is.

## Saves

Each game's saves live in your library, at `decrypted/<title id>/recomp/fs/savedata0/`. Encore keeps them when you
update. Copy that folder somewhere safe to back them up.

## Reporting a bug

1. When something goes wrong, press **F5** straight away. That marks the moment in the log and saves pictures of the
   last three seconds of frames.
2. Note what you were doing.
3. Back in the launcher, open the game's **⋯** menu and choose **Report a problem**. Encore gathers the game's logs
   from its last two sessions, the launcher's log, your settings and the pictures from your last F5 into one zip, then
   shows it in its folder. It holds no game files, saves or keys, and your home folder's name is left out of the logs.
4. Open an issue on [Encore's GitHub](https://github.com/BittahBandit1/Encore/issues) with the zip and your note.
   Without F5 pictures it's well under a megabyte; with them, up to a few tens of megabytes, so share it through a file
   host if it's too big to attach.

## Known issues

- **Persona 4: Dancing All Night:** story mode hasn't had a full playthrough yet.
- **Persona 3 and Persona 5:** still in testing.
- **All games**
  - The first build of each game takes minutes.
  - A Linux game folder on another drive needs that drive mounted before you play. On a drive shared with Windows, shut
    Windows down fully (not Fast Startup) so Linux can mount it.

## Troubleshooting

- **macOS says the app can't be opened, or is damaged.** Open System Settings, then Privacy & Security, and choose
  **Open Anyway** beside Encore.
- **A game won't build.** On a Mac, check that the Command Line Tools are installed: run `xcode-select --install` in
  Terminal. Send `session.log` if it still fails.
- **The game window closes as it starts.** Check that the game's files are still where you added them from, for example
  a drive that's no longer connected or mounted.
- **Windows says Smart App Control blocked a game.** Windows judges each new program once, and every game Encore builds
  is new to it, so now and then it refuses one. Choose **Rebuild and try again** in the dialog Encore shows: the rebuilt
  game is a new file, and Windows checks it afresh. If that's refused too, turn Smart App Control off in Windows
  Security, under App & browser control, then Smart App Control settings. On most versions of Windows 11 it can't be
  turned back on without reinstalling Windows.
