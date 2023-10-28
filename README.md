# Eddy

Eddy is a reference management software with a specific focus on the field of theoretical high-energy physics.

With Eddy you can
* browse the [INSPIRE](https://inspirehep.net/) and [arXiv](https://arxiv.org/) digital libraries
* open online documents
* maintain multiple databases of bibliographic entries
* organize your digital collection of books, articles, notes, …
* generate BibTeX code

> [!NOTE]
> Thank you to [arXiv](https://arxiv.org/) for use of its open access interoperability.
> Eddy was not reviewed or approved by, nor does it necessarily express or reflect the policies or opinions of, [arXiv](https://arxiv.org/).


## Alternatives

Eddy is inspired by applications such as [Mendeley](https://www.mendeley.com/) and [Zotero](https://www.zotero.org/), but mostly by the excellent [spires.app](https://member.ipmu.jp/yuji.tachikawa/spires/) developed by [Yuji Tachikawa](https://member.ipmu.jp/yuji.tachikawa/).

Despite Eddy following a somewhat different philosophy, the main reason for its existence is that [spires.app](https://member.ipmu.jp/yuji.tachikawa/spires/) is designed to run exclusively on Apple products. If you are a MacOS user, you should probably want to use [spires.app](https://member.ipmu.jp/yuji.tachikawa/spires/).

## Status

Eddy is considered stable, but still quite unpolished in terms of user experience. Not all planned features have been yet implemented, and the database format might change in the future.

Although for the most part, Eddy is fairly intuitive in its usage, proper documentation still needs to be written.

Contributions in the form of bug reports, feature requests, or better, code commits are welcome!

## Dependencies
Python packages:
* **Python** 3.8+
* **PySide2** 5.14+
* **feedparser**
* **pylatexenc** (optional)

Others:
* **KaTeX**

## Usage

First, run
```console
$ python eddyctl.py katex-download
```
to ensure proper rendering of the LaTeX code.

To launch Eddy, run
```console
$ python launcher.py
```

### Configuration

Eddy can be configured by editing the file `config.py`.

### Local databases

A local database can be created with
```console
$ python eddyctl.py new DATABASE_FILE
```
Local databases should be added to `config.py` by editing the relevant Python dictionary:
```python
LOCAL_DATABASES = {
    "Name_1": "DATABASE_FILE_1",
    "Name_2": "DATABASE_FILE_2",
    ...
}
```

## Known issues

Although developed to be multiplatform, so far, Eddy has been tested on Linux only, which is where the development happens. If you test Eddy on either Windows or MacOS, please let me know about any issues you might encounter.

Currently, editing a local database from two or more simultaneous instances of this software might lead to undefined behavior, and should be avoided.

## License

This project is licensed under the GNU General Public License v2.0.
