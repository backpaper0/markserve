# markserve — Browse and preview local Markdown files in your browser.

ローカルディレクトリに置かれたMarkdownファイルをブラウザでプレビューするCLIツールです。

## 機能

- HTTPサーバーを起動し、指定したディレクトリ配下のMarkdownファイルをHTMLプレビュー表示
- Mermaid.js記法の図をレンダリング
- サイドペインにファイルツリーを表示（大量のファイルがあるディレクトリを開いた場合は一部を省略して事故を防止）
- Markdown内のリンクをたどってページ遷移
- 画像ファイルはそのままプレビュー、それ以外のファイルはソースを表示
- Markdownはプレビュー/ソース表示をトグル可能（`?raw=1`）
- YAML Front matterを表形式でプレビュー表示（ソース表示時は元のYAMLをそのまま表示）

## インストール

```sh
uv tool install markserve
```

## 使い方

```sh
markserve [DIRECTORY] [-p/--port PORT] [-H/--host HOST] [-o/--open] \
  [-f/--pretty-font] [--css PATH] [--show-hidden NAME] \
  [--base-url PATH | --code-server] [--version]
```

- `DIRECTORY`: プレビュー対象のルートディレクトリ（省略時はカレントディレクトリ）
- `-p`, `--port`: 待ち受けポート（既定: `8000`）
- `-H`, `--host`: 待ち受けホスト（既定: `127.0.0.1`）
- `-o`, `--open`: 起動後にブラウザを自動で開く
- `-f`, `--pretty-font`: 読みやすさ重視のフォント（Windows: UD デジタル教科書体 / macOS: 游教科書体・Osaka）を使用する
- `--css PATH`: 指定したCSSファイルでデザイン（フォントなど）を上書きする
- `--show-hidden NAME`: ドット始まりでも表示対象に含める名前を指定する（階層を問わず一致。複数指定可）
- `--base-url PATH`: リバースプロキシ配下などサブパスで公開する場合のベースURL（例: `/docs`）。プロキシ側でこのパスを取り除いてから転送する構成を想定しており、markserve自身はprefixなしのパスでリクエストを受け取る。指定するとレンダリング結果のページ内のリンクやCSSファイルの読み込みURLにこのパスを付与する
- `--code-server`: code-serverのポートフォワーディング（`/proxy/<port>`）配下での実行に合わせて`--base-url /proxy/<port>`を自動設定する（`--base-url`とは併用不可）

例:

```sh
markserve ./docs -p 8765 -o
```

## 開発

```sh
uv sync
uv run pytest
uv run markserve examples/docs -p 8765 -o
```

`mise run dev` でも同じようにexamples/docsを対象にmarkserveを起動できます。
