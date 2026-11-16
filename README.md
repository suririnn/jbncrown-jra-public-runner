# JBN CROWN / JRA 2026 research engine — **code-only public candidate**

**公開用デモ計算基盤です。** 新しい公開リポジトリに安全確認済みのコードだけを置くために、新規作成しました。既存の非公開リポジトリを公開、fork、mirrorしたものではありません。

## できること

- JRAに限定した3条件: **① 最低単勝オッズ、② 単勝9.9倍以下の頭数、③ 馬連9.9倍以下の組数**。
- **①②③ / ①② / ①③ / ②③ / ① / ② / ③** の7視点と市場全体基準。
- 単勝・複勝・馬連・ワイド・馬単・3連複・3連単の保存済み全組オッズについて、券種別6区分を合算する汎用計算関数。
- 単勝帯／複勝帯の馬ごとの実測1・2・3着率、**A1–A4・B1–B4・C1–C4** の12記述研究系列。馬単と3連単は順序付き、ワイドと3連複は順不同。**各馬の着順率を掛けただけで的中確率にはしない**。
- 1～11月の11分割処理と、月別率を平均せず**分子・分母を合計して統合**するロジック。
- 取消・全組欠落・非JRA混入・組番号重複・月跨ぎ重複・倍率帯不一致を拒否する安全検査。
- 公式結果の独立証拠がないレースは的中・払戻の分母に加算しない。

## **まだできないこと（重要）**

この初期版に**実際のJRA公式サイトからの7券種スクレイピングや非公開原簿の自動取り込みはありません**。公開Actionsは11件の架空レースで計算ロジックを動作検証するだけです。実際の2026年1～11月全レースを取得した証明、正式モデルの学習・復元、LL/Brier/ECE、正式採用、新レース発走前実証の成功を主張しません。

既存private側の実レースオッズ・払戻をこのpublic repoへコピーせずに分析する受け渡し経路（およびJRAの情報利用条件）の確認は別作業です。**privateへのアクセスキー・PAT・GitHub Secretsをこの公開例に追加しないでください。**

`config/DEMO_ONLY_*` の倍率帯は大部分が**架空検査用**です。ユーザーの既存馬連6帯 `[5,10,20,50,100]` は一致しますが、残り6券種・払戻帯は本番の固定帯ではありません。学習期間だけで固定した境界を、本番の非公開環境で渡す設計としてください。

## 再現方法（Python 3.12 / 標準ライブラリのみ）

```bash
python examples/create_synthetic.py
python -m unittest discover -s tests -v
python run_month.py --month 01 --input-dir examples/synthetic --output-dir .demo_outputs --demo-only
for m in 02 03 04 05 06 07 08 09 10 11; do
  python run_month.py --month "$m" --input-dir examples/synthetic --output-dir .demo_outputs --demo-only
done
python merge_months.py --input-dir .demo_outputs --output .demo_outputs/merged.json --demo-only
```

GitHub Actionsでのデモ実行は現在停止中です（YAMLの原本は `.github/workflows-paused/20261116-synthetic-demo/` に保管）。上記のPythonコマンドで11か月分の架空データをローカルで検査・統合できます。**実レースの自動収集は行いません。**

## 公開リポジトリを使う際の注意（元のprivateリポジトリはそのまま）

1. 同じGitHubアカウントで [github.com/new](https://github.com/new) を開く。
2. 例: `jbncrown-jra-public-runner` を新規作成し、**Public**にする。既存privateリポジトリをPublicへ変更しない。
3. 新しい空リポジトリのURLを現在のチャットへ伝える。接続権限がある場合、こちらで安全確認済みコードをその新リポジトリへ投入できる。GitHub Appの対象リポジトリ権限が限定されている場合は、GitHub接続の許可が必要。
4. ZIPの直接アップロードはバックアップ手段。**既存のprivateリポジトリをfork/clone/mirrorしない。**
5. リポジトリ作成後、公開ソースとActions出力を確認する。実データ連携は別の安全審査後。

## 設計上の境界

- `synthetic_demo`: 架空データ。実レース成果には加算禁止。
- `officially_scored_races`: 入力レコード上で独立検証済みとして認識した件数。**架空デモでは架空の検証件数**。
- `NOT_prestart_validation`: 過去最終オッズ研究は発走前予測ではない。
- 本格的な①②③実験と12系列の採否には、レース外の未来情報を含まない時系列独立検証と、正式な的中組・払戻原票が別途必要。

## 利用条件

本配布物には第三者のソースコード・画像・モデル・レース原簿は含めていません。ソフトウェアライセンスは所有者が決めるため、このテンプレートでは自動付与していません。
