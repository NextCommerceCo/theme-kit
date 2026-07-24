<!-- Badges -->
[![PyPI Version][pypi-v-image]][pypi-v-link]
[![Build Status][GHAction-image]][GHAction-link]
[![CodeCov][codecov-image]][codecov-link]

# Next Commerce Theme Kit

Theme Kit is a cross-platform command line tool to build and maintain storefront themes with [Sass Processing](#sass-processing) support on the Next Commerce platform.

## Installation

Theme Kit is a python package available on [PyPi](https://pypi.org/project/next-theme-kit/)

If you already have `python` and `pip`, install with the following command:

```
python -m pip install next-theme-kit
```

#### Mac OSX Requirements
See how to install `python` and `pip` with [HomeBrew](https://docs.brew.sh/Homebrew-and-Python#python-3x). Once you have completed this step you can install using the `pip` instructions above.

#### Windows Requirements

* **Option 1 (Recommended)** - Windows 10 and above feature WSL (Windows Subsystem for Linux) which provides a native Linux environment, see how to [Install WSL with Ubuntu](https://docs.microsoft.com/en-us/windows/wsl/install). Once you have installed WSL, follow the [best practice guides to configure and use with VS Code](https://docs.microsoft.com/en-us/windows/wsl/setup/environment) and then follow the `pip` instructions above to install Theme Kit.

* **Option 2** - Installing `python` in Windows natively can be done with through the [Windows App Store](https://apps.microsoft.com/store/detail/python-39/9P7QFQMJRFP7?hl=en-us&gl=us). Recommend using [Windows Powershell](https://apps.microsoft.com/store/detail/powershell/9MZ1SNWT0N5D?hl=en-us&gl=us). This route is a little more tricky and some knowledge on how to manage python in windows will be required.

> **Use Python Virtual Environments** - For Mac, Windows, and Linux, it's a best practice to use a Python Virtual Environment to isolate python packages and dependecies to reduce potential conflicts or errors, [more on creating a Python Virutal Environment](https://www.freecodecamp.org/news/how-to-setup-virtual-environments-in-python/).


#### Updating Theme Kit

Update to the latest version of Theme Kit with the following command:
```
python -m pip install next-theme-kit --upgrade
```

> :warning: **Important**
>
> As of version 1.0.2, the store authentication uses Oauth and requires creating a store **Oauth App** with `themes:read` and `themes:write` permissions.

## Usage
With the package installed, you can now use the commands inside your theme directory and work on a storefront theme.

**Available Commands**
* `ntk init` - initialize a new theme
* `ntk list` - list all available themes
* `ntk checkout` - checkout an existing theme
* `ntk pull` - download existing theme or theme file
* `ntk push` - push current theme state to store
* `ntk watch` - watch for local changes and automatically push changes to store
* `ntk sass` - process sass to css, see [Sass Processing](#sass-processing)

**Important** - You must pass the `apikey` and `store` parameters for all commands **if** there is not an existing `config.yml` file in your current directory.

#### Init
Initialize a new theme which will create the theme on a store and create an initial config.yml file

```
ntk init --name="<Theme Name>" --apikey="<api key>" --store="<https://storedomain.com>"
```
##### Required flags without config.yml
| Short | Long | Description|
|--- | --- | --- |
| -a | --apikey | API Key used to connect to the store.|
| -s | --store | Full domain of the store. |
| -n | --name | Name of the new theme |


#### List
List all themes installed on the theme.
```
ntk list --apikey="<api key>" --store="<https://storedomain.com>"
```
##### Required flags without config.yml
| Short | Long | Description|
|--- | --- | --- |
| -a | --apikey | API Key used to connect to the store.|
| -s | --store | Full domain of the store. |


#### Checkout
Checkout a theme from your store to pull it into your directory.
```
ntk checkout --theme_id=<id> --apikey="<api key>" --store="<https://storedomain.com>"
```
##### Required flags without config.yml
| Short | Long | Description|
|--- | --- | --- |
| -a | --apikey | API Key used to connect to the store.|
| -s | --store | Full domain of the store. |
| -t | --theme_id | ID of the theme. |

#### Pull
Pull a theme from your store to into your directory.
```
ntk pull --theme_id=<id> --apikey="<api key>" --store="<https://storedomain.com>"
```
##### Required flags without config.yml
| Short | Long | Description|
|--- | --- | --- |
| -a | --apikey | API Key used to connect to the store.|
| -s | --store | Full domain of the store. |
| -t | --theme_id | ID of the theme. |


#### Push
Push all theme files from your local directory to the store.
```
ntk push --theme_id=<id> --apikey="<api key>" --store="<https://storedomain.com>"
```
##### Required flags without config.yml
| Short | Long | Description|
|--- | --- | --- |
| -a | --apikey | API Key used to connect to the store.|
| -s | --store | Full domain of the store. |
| -t | --theme_id | ID of the theme. |


#### Watch
Watch for file changes and additions in your local directory and automatically push them to the store.
```
ntk watch --theme_id=<id> --apikey="<api key>" --store="<https://storedomain.com>"
```
##### Required flags without config.yml
| Short | Long | Description|
|--- | --- | --- |
| -a | --apikey | API Key used to connect to the store.|
| -s | --store | Full domain of the store. |
| -t | --theme_id | ID of the theme. |

#### Sass
Process `sass` files to CSS files for inclusion in your storefront. See [Sass Processing](#sass-processing) for more details.

```
ntk sass
```
##### Optional flags
| Short | Long | Description|
|--- | --- | --- |
| -sos | --sass_output_style |  Options are nested, expanded, compact, or compressed|



## Sass Processing
Theme kit includes support for Sass processing via [Python Libsass](https://sass.github.io/libsass-python/). Sass processing includes support for variables, imports, nesting, mixins, inheritance, custom functions, and more.

**How it works**
1. Put `scss` files in top level `sass` directory.
2. Run `ntk sass` or `ntk watch` to process theme `sass` files.
3. Top level `scss` files will be processed to `css` files in the asset directory with the same name.

**Example Theme with Sass Structure**
```
├── assets
│   ├── styles.css // reference this asset file in templates
├── sass
│   ├── _base.scss
│   ├── _variables.scss
│   └── styles.scss // processed to assets/main.css
```

**Important** - Sass processing is only supported on local, files in the `sass` directory are uploaded to your store for storage but cannot be edited in the store theme editor.

**Configure Default Output Style**

Change the default sass output style in `config.yml`, example below.

```
development:
  apikey: <api key>
  sass:
    output_style: compressed // options: nested, expanded, compact, or compressed
  store: <store url>
  theme_id: <theme id>
```


<!-- Badges -->
[codecov-image]: https://codecov.io/gh/29next/theme-kit/branch/master/graph/badge.svg?token=LPUOTZ5MZ5
[codecov-link]: https://codecov.io/gh/29next/theme-kit
[pypi-v-image]: https://img.shields.io/pypi/v/next-theme-kit.svg
[pypi-v-link]: https://pypi.org/project/next-theme-kit/
[GHAction-image]: https://github.com/NextCommerceCo/theme-kit/actions/workflows/test.yml/badge.svg?branch=master
[GHAction-link]: https://github.com/NextCommerceCo/theme-kit/actions?query=event%3Apush+branch%3Amaster
