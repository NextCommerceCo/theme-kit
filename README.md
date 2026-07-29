<!-- Badges -->
[![PyPI Version][pypi-v-image]][pypi-v-link]
[![Build Status][GHAction-image]][GHAction-link]
[![CodeCov][codecov-image]][codecov-link]

# Next Commerce Theme Kit

[Theme Kit](https://github.com/NextCommerceCo/theme-kit) is a command line tool for developers to build and maintain storefront themes programmatically, allowing theme developers to:

- Work on theme templates and assets using their local code editor or favorite IDE.
- Use git version control to work on a theme collectively with many theme collaborators.
- Use a pipeline to manage deployments of theme updates.

## Installation

Theme Kit is a Python package available on [PyPi](https://pypi.org/project/next-theme-kit/).

If you already have `python` and `pip`, install with the following command:

```bash
pip install next-theme-kit
```

The core CLI is pure Python and installs on macOS (including Apple Silicon), Linux, and native Windows.
Install optional features only when a project needs them:

```bash
pip install 'next-theme-kit[sass]'     # legacy libsass compilation
pip install 'next-theme-kit[capture]'  # screenshot capture; then: playwright install chromium
```

#### Mac OSX Requirements
See how to install `python` and `pip` with [HomeBrew](https://docs.brew.sh/Homebrew-and-Python#python-3x). Once you have completed this step you can install using the `pip` instructions above.

#### Windows Requirements

* **Option 1 (Recommended)** — Windows 10 and above feature WSL (Windows Subsystem for Linux) which provides a native Linux environment, see how to [Install WSL with Ubuntu](https://docs.microsoft.com/en-us/windows/wsl/install). Once you have installed WSL, follow the [best practice guides to configure and use with VS Code](https://docs.microsoft.com/en-us/windows/wsl/setup/environment) and then follow the `pip` instructions above to install Theme Kit.
* **Option 2** — Installing `python` in Windows natively can be done through the [Windows App Store](https://apps.microsoft.com/store/detail/python-39/9P7QFQMJRFP7?hl=en-us&gl=us). Recommend using [Windows Powershell](https://apps.microsoft.com/store/detail/powershell/9MZ1SNWT0N5D?hl=en-us&gl=us). This route is a little more tricky and some knowledge on how to manage Python in Windows will be required.

> [!TIP]
> **Use Python Virtual Environments** — For Mac, Windows, and Linux, it's a best practice to use a Python Virtual Environment to isolate Python packages and dependencies to reduce potential conflicts or errors, [more on creating a Python Virtual Environment](https://www.freecodecamp.org/news/how-to-setup-virtual-environments-in-python/).

## Setup

Connect `ntk` to a store in three steps.

### 1. Create the API Key

Store authentication uses [OAuth 2.0](https://auth0.com/intro-to-iam/what-is-oauth-2/) and requires creating a store OAuth App with the `themes:read` and `themes:write` permissions.

1. In the Storefront admin, go to **Settings > API Access**.
2. Click **Create App**.
3. Give the app a name and assign a user.
4. In the **Permissions** tab, enable `themes:read` and `themes:write`.
5. **Save**. Copy the generated API key — you will need it in the next step.

### 2. Configure Theme Kit

`ntk` reads its connection settings from two places: command flags (`--apikey`, `--store`, `--theme_id`) and the `config.yml` file in your theme directory. You do not need to create `config.yml` by hand — `ntk checkout` and `ntk init` write it for you, and after that commands run without flags:

```yaml
development:
  apikey: <api key>
  store: https://{store}.29next.store
  theme_id: <theme id>
```

> [!WARNING]
> Keep the API key out of source control. Do not commit `config.yml` to git if it contains the key.

> [!NOTE]
> `config.yml` supports multiple environments. Commands use the `development` entry by default; pass `-e` / `--env` to target another environment (for example `ntk push --env=production`). The `[development]` prefix in command output is the active environment.

### 3. Connect to a Theme

Work from a copy of an existing theme rather than an empty directory — a complete theme is the reference for the required directories, templates, and settings.

**Work on a theme already on the store** — `ntk checkout` downloads the theme into your current directory and writes `config.yml`:

```bash
ntk checkout --theme_id=<id> --apikey="<api key>" --store="https://{store}.29next.store"
```

**Add a new theme to the store** — start from a copy of an existing theme, such as the [Intro Bootstrap](https://github.com/NextCommerceCo/intro-bootstrap) starter theme, then register it as a new theme with `ntk init` and upload the files with `ntk push`:

```bash
ntk init --name="<Theme Name>" --apikey="<api key>" --store="https://{store}.29next.store"
ntk push
```

## Usage

With the package installed, you can now use the commands inside your theme directory and work on a storefront theme.

| Command        | Description |
| -------------- | ----------- |
| `ntk init`     | Initialize a new theme |
| `ntk list`     | List all available themes |
| `ntk checkout` | Checkout an existing theme |
| `ntk pull`     | Download existing theme or theme file |
| `ntk push`     | Push current theme state to store |
| `ntk watch`    | Watch for local changes and automatically push changes to store |
| `ntk sass`     | Process sass to css, see [Sass Processing](#sass-processing) |
| `ntk validate` | Validate theme files locally or against the store |
| `ntk capture`  | Capture deterministic desktop and mobile PNGs |

### Browse Store Themes

To see what themes exist on the store, run `ntk list` to print the theme ID and name of each, with the active theme marked.

```bash
ntk list
```

Output looks like:

```
[development] Available themes:
[development] 	[42] 	Spring Launch
[development] 	[43] 	Holiday Promo (Active)
```

If you do not have a `config.yml`, also pass `--apikey` and `--store`.

### Work on an Existing Theme

To start working on a theme that already exists on the store, `ntk checkout` downloads it into your directory and writes `config.yml` with the theme ID.

```bash
ntk checkout --theme_id=<id>
```

`--theme_id` / `-t` is required. If you do not have a `config.yml`, also pass `--apikey` and `--store`:

```bash
ntk checkout --theme_id=<id> --apikey="<api key>" --store="https://{store}.29next.store"
```

`ntk checkout` differs from `ntk pull` in one way: `checkout` writes `config.yml` so the directory is ready for subsequent `ntk push` / `ntk watch` runs; `pull` downloads the same files without writing `config.yml`.

### Add a New Theme to the Store

`ntk init` registers your current directory as a new theme on the store and writes a `config.yml`. It does not download or scaffold any files — run it inside an existing theme codebase, then `ntk push` to upload the files.

> [!WARNING]
> Building a theme from an empty directory is not advised. Start from a copy of a complete theme — the [Intro Bootstrap](https://github.com/NextCommerceCo/intro-bootstrap) starter theme or an existing theme from your store via [`ntk checkout`](#work-on-an-existing-theme).

```bash
ntk init --name="<Theme Name>"
```

`--name` / `-n` is required. If you do not have a `config.yml` yet, also pass `--apikey` and `--store`:

```bash
ntk init --name="<Theme Name>" --apikey="<api key>" --store="https://{store}.29next.store"
```

On success, `ntk init` logs the new theme ID and name, and persists the theme ID into `config.yml` so subsequent commands can omit `--theme_id`.

### Sync Files to the Store

To sync files between your local directory and the store, use `ntk push` to upload and `ntk pull` to download. Both upload or download the whole theme by default, and both accept file paths as positional arguments to limit the operation to specific files.

> [!NOTE]
> File paths are relative to the theme root. `ntk push` only uploads files inside the theme directories (`assets`, `checkout`, `configs`, `layouts`, `locales`, `partials`, `sass`, `templates`) with valid theme file extensions. Explicit unsupported or missing paths are reported as rejected and make the command fail.

| Example | Command |
| ------- | ------- |
| Push a single file | `ntk push templates/index.html` |
| Push a subset of files | `ntk push templates/index.html assets/main.css` |
| Pull a single file | `ntk pull templates/index.html` |
| Pull a subset of files | `ntk pull templates/index.html assets/main.css` |

### Watch for File Changes

`ntk watch` monitors your theme directory and automatically pushes changed files to the store. Use it while you develop — save a file and the change is uploaded moments later.

```bash
ntk watch
```

On start, `ntk watch` logs the store, theme ID, a preview-theme URL, and the directory it is watching. Press `Ctrl + C` to stop.

> [!WARNING]
> Deletes sync too — deleting a local file while `ntk watch` is running deletes that file from the theme on the store.

> [!NOTE]
> `ntk watch` only uploads files with valid theme extensions. It does not accept file arguments. To scope changes to specific files, run `ntk push` with file paths instead.

### Validate Before Upload

Run deterministic local checks for JSON syntax, template block balance, supported paths, and unsafe custom-product inheritance:

```bash
ntk validate templates/catalogue/product.subscription.html configs/settings.json
```

Add `--server` to submit locally valid text files to the platform's template validator without saving them:

```bash
ntk validate --server templates/catalogue/product.subscription.html
```

Local validation does not claim to prove a complete runtime render. Server validation requires the store, API key, and theme ID from flags or `config.yml`.

### Capture Reproducible Screenshots

With the `capture` extra and Chromium installed, capture real rendered PNGs at the fixed 1440px desktop and 390px mobile widths:

```bash
ntk capture --url="/?preview_theme=<theme-id>&skip_cache=1" \
  --output=qa-output --viewports=desktop,mobile --json --no-progress
```

Capture waits for network idle, web fonts, lazy-loaded content, and images before writing full-page PNGs. It is suitable for local use and CI; it never substitutes DOM metrics for visual evidence.

### Automation Output

Every finite command accepts `--json`, `--quiet`, and `--no-progress`. `--json` writes exactly one versioned result object to stdout; logs stay on stderr, and progress is automatically disabled for JSON and non-interactive output. Push/pull/validation results are reported per file. Authentication, network, validation, rejection, and partial-transfer failures return a non-zero exit status.

The JSON envelope is stable within schema version `1`:

```json
{"schema_version":"1","command":"push","ok":true,"count":1,"results":[{"path":"templates/index.html","status":"uploaded"}]}
```

### Sass Processing

Theme kit includes support for Sass processing via [Python Libsass](https://sass.github.io/libsass-python/). Sass processing includes support for variables, imports, nesting, mixins, inheritance, custom functions, and more.

> [!WARNING]
> Sass processing is only supported on local, files in the `sass` directory are uploaded to your store for storage but cannot be edited in the store theme editor.

**How it works**

1. Put `scss` files in top level `sass` directory.
2. Run `ntk sass` or `ntk watch` to process theme `sass` files.
3. Top level `scss` files will be processed to `css` files in the asset directory with the same name.

**Example Theme with Sass Structure**

```
├── assets
│   ├── main.css // reference this asset file in templates
├── sass
│   ├── _base.scss
│   ├── _variables.scss
│   └── main.scss // processed to assets/main.css
```

<!-- Badges -->
[codecov-image]: https://codecov.io/gh/29next/theme-kit/branch/master/graph/badge.svg?token=LPUOTZ5MZ5
[codecov-link]: https://codecov.io/gh/29next/theme-kit
[pypi-v-image]: https://img.shields.io/pypi/v/next-theme-kit.svg
[pypi-v-link]: https://pypi.org/project/next-theme-kit/
[GHAction-image]: https://github.com/NextCommerceCo/theme-kit/actions/workflows/test.yml/badge.svg?branch=master
[GHAction-link]: https://github.com/NextCommerceCo/theme-kit/actions?query=event%3appush+branch%3amaster
