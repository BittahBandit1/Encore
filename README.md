# Encore

**The Persona Dancing games for PS Vita, rebuilt to run natively on your Mac, PC or Steam Deck.**

Encore takes your own copy of a Persona Dancing game, recompiles it into a native program on your computer, and runs
it at higher resolutions and frame rates than the Vita ever could. No emulator, and nothing of the game is included:
you bring the games you own.

| Game | Title ID | Status |
|---|---|---|
| Persona 4: Dancing All Night (US) | PCSE00764 | Playable |
| Persona 3: Dancing in Moonlight (US) | PCSE01274 | Playable, in testing |
| Persona 5: Dancing in Starlight (US) | PCSE01275 | Playable, in testing |

Only the US releases play so far. Other regions and versions are recognised, and the launcher tells you which release
it supports.

## What you get

- **Sharper than the Vita:** render at up to 6x the Vita's resolution (F2 cycles it in game).
- **60 fps:** the dances keep time with the music. Persona 3 and 5 also run their menus at 60.
- **Your DLC:** the songs and costumes you own, decrypted from your own dump.
- **Texture packs:** packs made for Vita3K work unchanged, such as the PS4 texture pack for Persona 3.
- **No close-up blur** in Persona 4: the Vita draws those shots at quarter resolution and stretches them back. Encore
  keeps them sharp (you can turn the blur back on).
- **Controller, keyboard or touch screen**, with your saves kept in one library folder.

## What you need

- **A computer:** a Mac with Apple silicon (macOS 11 or newer), a Windows 10 or 11 PC, or a Linux PC, including the
  Steam Deck.
- **Your own copies of the games**, dumped from a Vita you own: the game, its update if it has one, and any DLC
  (`ux0:app`, `ux0:patch` and `ux0:addcont`).
- **Sony's PS Vita system software update file** (`PSVUPDAT.PUP`), free from Sony's website. Encore rebuilds the Vita's
  system libraries from it on your machine. If you've set up Vita3K, you've already downloaded this file once.

**No game code, game data or firmware is in this repository, and none ever will be.** Please don't open issues asking
for them.

## Playing

There's no Encore release to download yet. Until there is, build it from source (below).

Once it's installed, the launcher walks you through first-run setup: point it at your firmware file and your game
dumps, and it decrypts and checks them. The first time you play a game, Encore builds it for your computer, which takes
a few minutes. After that it starts straight away.

The [player guide](docs/player-guide.md) covers installing, controls, settings, saves and reporting a bug. Each game's
own notes and options are in its pack: [Persona 4](packs/PCSE00764/README.md),
[Persona 3](packs/PCSE01274/README.md) and [Persona 5](packs/PCSE01275/README.md).

## Building from source

Encore builds on macOS, Linux and Windows. From the top of a checkout:

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
launcher/build.sh          # the launcher: launcher/nativ
```

On a Mac, build the libraries once first with `runtime/platform/macos/setup-toolchain.sh`. To make a self-contained
install a player can run, use `dev/macos-install.sh <folder>` (makes `Encore.app`), `dev/windows-install.sh <folder>` or
`dev/linux-install.sh <folder>`.

You can also run each step yourself with `./vitarecomp` (on Windows, `.venv\Scripts\python.exe pipeline\vitarecomp.py`).
Run it with no arguments for the full list:

| Command | What it does |
|---|---|
| `firmware <PUP>` | Decrypts Sony's firmware update file. |
| `scan <folder>` | Finds games, updates and firmware files in a folder, at any depth. |
| `add <copy>` | Adds a game or its update. `import` takes one that's already decrypted. |
| `analyze <title>`, `recompile <title>`, `build <title>` | Finds the game's functions, translates them to C and compiles them. |
| `run <title>` | Plays it. |

Your games, firmware, builds and saves live in one library folder, kept apart from the install:
`~/Library/Application Support/ProjectNativ/Nativ/library` on macOS, `~/.local/share/ProjectNativ/Nativ/library` on
Linux and `%LOCALAPPDATA%\ProjectNativ\Nativ\library` on Windows (or `dump/` inside a checkout). The folder keeps
Project Nativ's name, so an existing library works as it is.

## How it works

A Vita game is ARM code written against Sony's system software, and Encore handles the two separately:

- **The game's code is recompiled.** A static recompiler translates the game's ARMv7 code into C once, ahead of time,
  and that C is compiled into a native program.
- **The system underneath is rebuilt.** Sony's own libraries that the game loads are recompiled with it from your
  firmware. Below them, a runtime stands in for the Vita's kernel and hardware: it runs the game's threads, draws its
  graphics on your GPU and plays its sound.

The technical documentation goes deeper: [how it works](docs/architecture.md), [working on it](docs/developers.md),
[the runtime](docs/runtime.md), [debugging a game](docs/debugging.md), [verification](docs/verification.md),
[the shader compiler](docs/shader-compiler.md) and [the Vita's GPU instruction set](docs/usse-isa.md). These come from
Project Nativ and use its name, and some of its other games as examples.

## Credits

Encore stands on other people's work:

- **[Project Nativ](https://github.com/TheLostPantheon/nativ)** by TheLostPantheon and its contributors: the recompiler,
  runtime and pipeline that everything here runs on. If you'd like to support it, its developer has a
  [Ko-fi](https://ko-fi.com/kingtorro).
- **[PersonaDancingRecomp](https://github.com/Ecstatic-Magician/PersonaDancingRecomp)** by Ecstatic-Magician: the
  Persona Dancing game packs and renderer fixes that Encore is forked from.
- The third-party libraries listed in [THIRD_PARTY.md](THIRD_PARTY.md), each under its own licence.
- **Atlus** made the games, and Dingo developed Persona 4: Dancing All Night. Please support them by buying them.

Encore is an unofficial fan project. It isn't affiliated with or endorsed by Atlus, SEGA or Sony, and Persona is a
trademark of Atlus. It contains no Sony or game code: the games are decrypted and recompiled on your machine and never
leave it.

## Licence

Encore is free software under the GNU General Public License, version 2 or (at your option) any later version, the same
as Project Nativ: see [LICENSE](LICENSE). It's a modified version of PersonaDancingRecomp and Project Nativ; the git
history records what changed. Third-party code keeps its own licence (see [THIRD_PARTY.md](THIRD_PARTY.md)).

## AI disclaimer

Like Project Nativ, Encore is developed with the help of AI tools: much of its code and documentation was written with
AI assistance, under its maintainer's direction, and tested on the games themselves.
