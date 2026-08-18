# Mermaid図のサンプル

```mermaid
graph TD
    A[ブラウザ] -->|GET /index.md| B(markserveサーバー)
    B -->|Markdown読み込み| C[ファイルシステム]
    B -->|HTMLレンダリング| A
```

[トップへ戻る](index.md)
