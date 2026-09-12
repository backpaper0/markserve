# Mermaid図のサンプル

```mermaid
graph TD
    A[ブラウザ] -->|GET /index.md| B(markserveサーバー)
    B -->|Markdown読み込み| C[ファイルシステム]
    B -->|HTMLレンダリング| A
```

# Vega-Liteグラフのサンプル

```vega-lite
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "description": "サンプルの棒グラフ",
  "data": {
    "values": [
      {"category": "A", "value": 28},
      {"category": "B", "value": 55},
      {"category": "C", "value": 43}
    ]
  },
  "mark": "bar",
  "encoding": {
    "x": {"field": "category", "type": "nominal"},
    "y": {"field": "value", "type": "quantitative"}
  }
}
```

# 画像のサンプル

クリックすると別タブで拡大表示できます。

![サンプル画像](image.png)

[トップへ戻る](index.md)
