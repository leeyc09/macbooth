# Macbooth Template Studio (local admin)

A small local web app to design **pibooth** picture templates visually and wire
them straight into your local pibooth installation. It serves the same editor
that runs on the web, but connected to your machine, so it can:

- **Save** a template directly into your pibooth configuration folder.
- **Preview** it with the *real* pibooth rendering engine (the exact printed
  result), using numbered placeholder photos.
- **Register** it in `pibooth.cfg` (`[PICTURE] template` and `[GENERAL] plugins`),
  merging with any templates already listed.

## Requirements

The same environment as pibooth, plus the `webcam` extra is not needed here.
From the repository root:

```bash
python3 -m venv ~/pibooth-venv
~/pibooth-venv/bin/pip install -e ".[dslr,printer]"   # pibooth itself (PIL is enough for previews)
```

## Run

```bash
~/pibooth-venv/bin/python admin/pibooth_admin.py
```

It opens <http://localhost:8080> in your browser. Options:

| Option          | Meaning                                             |
| --------------- | --------------------------------------------------- |
| `--config DIR`  | pibooth config folder (default `~/.config/pibooth`) |
| `--port N`      | port to serve on (default `8080`)                   |
| `--no-browser`  | do not open the browser automatically               |

## How it works

The page detects the local backend (`GET /api/ping`). When present it reveals a
**Connected to pibooth** panel with the extra buttons; opened as a plain file or
as the published web artifact, the same page falls back to copy/paste export.

API (all JSON unless noted):

| Method & path            | Purpose                                             |
| ------------------------ | --------------------------------------------------- |
| `GET  /api/ping`         | health check + config folder                        |
| `GET  /api/templates`    | list templates in the config folder                 |
| `GET  /api/template/<f>` | load one `.json` template                           |
| `POST /api/template`     | save a template JSON, returns the file name         |
| `POST /api/preview`      | render with the pibooth engine, returns a PNG       |
| `POST /api/register`     | add the template + plugin to `pibooth.cfg`          |

Templates use the format read by `plugins/pibooth_picture_template.py` (see its docstring).
