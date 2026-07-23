# UMG Widget-Layer Transitions — 実装前検討メモ

- 日付: 2026-07-23
- ベース: v1.3.0 (`8e6d36c`)
- ステータス: 実装前調査(未着手)

## 1. 目的

現行の PostProcess 方式は UMG/Slate UI レイヤーを覆えない(README Limitations 明記)。
全画面ウィジェットとしてトランジションマテリアルを描画する代替レンダリングパスを追加し、
UI の上にトランジションを被せられるようにする(Roadmap: `High`)。

## 2. 現状アーキテクチャの調査結果

- `ITransitionEffect`(`Initialize / UpdateProgress / Cleanup / SetInvert / SetParameters`)は
  レンダリング方式に依存しない抽象になっており、**インターフェース変更なしで**
  ウィジェット実装を追加できる。
- エフェクト生成はプリセットの `EffectClass` 経由(`TransitionManagerSubsystem.cpp` の
  Create Effect 節)。プール(`TMap<UClass*, FTransitionEffectPool>`)もクラス単位なので
  新クラスはそのまま共存できる。ホットスワップ(シーケンス間の1フレーム重ね)も
  クラス不一致時のパスが既にあり、widget↔postprocess の混在シーケンスも成立する。
- ランタイムモジュールの `Build.cs` は既に `UMG / Slate / SlateCore` に依存済み。
  ビルド設定の変更は不要。
- 既存28マテリアルは PostProcessVolume の `WeightedBlendables` で使用されており、
  マテリアルドメインは Post Process(UI ドメインではない)。
  **UI(UserInterface)ドメインのマテリアルでなければ Slate/UMG ブラシには使えない**ため、
  既存マテリアル資産をそのまま流用することはできない。
- エディタプレビュー(`TransitionPreviewViewport`)も PostProcessVolume 方式。
  ウィジェットモードのプレビュー対応は別途必要(UIドメインなら `FSlateBrush` +
  `SetResourceObject` で素直に描画できる見込み)。
- SDF ロジックは `MaterialFunctions/`(9個の MF_*)に分離されているため、
  エディタ作業で UI ドメイン版マスターマテリアルを作る際はグラフの大部分を再利用できる。

## 3. 設計方針(案)

### レンダリング

- 新クラス `UWidgetTransitionEffect`(`UObject` + `ITransitionEffect`)。
- C++のみで全画面 Slate ウィジェット(`SConstraintCanvas`/`SImage` + `FSlateBrush` に MID)を生成し、
  `UGameViewportClient::AddViewportWidgetContent(Widget, ZOrder)` で追加。
  高い ZOrder を指定すれば `AddToViewport` された UMG より上に描画される。
  ※ UUserWidget/WidgetBlueprint 資産は不要 = Blueprint-only プロジェクトでも動く。
- ウィジェットは `EVisibility::HitTestInvisible` にして入力を透過
  (入力ブロックは従来どおり `bAutoBlockInput` がサブシステム側で担当)。
- `Preset->Priority` はウィジェットモードでは ZOrder として解釈(要ドキュメント化)。
- `Initialize` が受け取る `UWorld*` から `World->GetGameViewport()` を辿れるため、
  インターフェース変更は不要(破壊的変更なし)。

### データモデル(プリセット)

推奨案: `UTransitionPreset` に追加
- `ERenderingMode RenderingMode`(PostProcess = 既定 / WidgetLayer)
- `TObjectPtr<UMaterialInterface> WidgetTransitionMaterial`(UIドメイン用スロット、
  WidgetLayer 時のみ EditCondition で表示)

代替案(不採用): DA_*_Widget を28個複製 → 資産倍増・保守コスト大。
EffectClass の差し替えだけで済ませる案はマテリアルドメイン不一致が残るため単独では不成立。

### パラメータ互換

`Progress / Invert / FadeColor` の各パラメータ名・警告ロジック(`SetParameters` の
missing-parameter warning)は MID ベースなのでそのまま流用可能。

## 4. Claude(この環境)で完結する作業 / しない作業

### 完結する(C++/ドキュメント)

- `UWidgetTransitionEffect` 新規実装(Slate 全画面ウィジェット、MID 管理、ZOrder)
- `UTransitionPreset` の `RenderingMode` / `WidgetTransitionMaterial` 追加
- サブシステム側の統合(必要なら)・ログ/警告の整備
- エディタプレビューパネルのウィジェットモード対応(Slate ブラシ描画パス)
- README(EN/JA)・FAQ・API Reference・CHANGELOG の更新
- (任意)Preset Validation(`IsDataValid`)にドメイン不一致チェックを追加

### 完結しない(UEエディタ/実機が必要)

1. **UI ドメイン版マテリアルの作成** — `.uasset` はバイナリかつ本リポジトリでは
   Git LFS 管理(この環境には実体が未取得)。28種の UI ドメイン版マスターマテリアル
   + インスタンスの作成はエディタでの手作業。MF_* の再利用で軽減はできるが最大の工数。
2. **SceneTexture 依存エフェクトの選別** — Pixelate / TVSwitchOff / Dissolve / Wind など
   シーンを歪める・サンプルする系は UI ドメインで SceneColor を参照できないため
   ウィジェットモードに移植不可の可能性が高い。どのエフェクトが対象かは
   エディタでマテリアルグラフを開かないと確定できない(→ 対応表の作成が必要)。
3. **コンパイル・動作検証** — UE 5.5 + VS2022 + Win64 環境が必要。この環境では
   ビルド不可のため、C++ はレビュー可能な品質で書くがコンパイル確認は人手。
4. **ZOrder 被覆の実機確認**(ユーザーUMGの上に確実に乗るか)、L_ShowCase 更新、
   プレビュー GIF 作成。

## 5. バージョニング判断: 1.4.0 を推奨

- 変更はすべて**追加的**: 新クラス、プリセットの新プロパティ(既定値 = 従来動作)、
  `ITransitionEffect` は無変更。既存プリセット・既存ユーザーコードはそのまま動く。
  → SemVer 上はマイナーバージョン(1.4.0)が妥当。
- 2.0.0 にすべきケース(今回は該当しない):
  - `ITransitionEffect` のシグネチャ変更(カスタムエフェクト実装者を破壊)
  - 既存プリセット資産の再保存を強制するスキーマ変更
  - 既定レンダリングモードの変更
- ただし初回リリースは「対応マテリアルは一部(例: Fade + ワイプ系数種)」となる
  可能性が高い。その場合も 1.4.0 で「Widget レイヤーモード(対応エフェクトは順次拡大)」
  として出し、残りのマテリアル移植を 1.4.x / 1.5.0 で積み増すのが現実的。

## 6. 実装フェーズ案

| フェーズ | 内容 | 担当 |
|---|---|---|
| A | C++ ランタイム(`UWidgetTransitionEffect` + プリセット拡張) | Claude |
| B | UI ドメイン版 M_Transition_Fade(最小検証用)作成・実機確認 | 人手(エディタ) |
| C | プレビューパネル対応 + ドキュメント + Validation | Claude |
| D | 対応可能エフェクトの UI ドメイン版マテリアル量産 + GIF | 人手(エディタ) |

## 7. 未解決の確認事項

- [ ] 各マテリアルの SceneTexture 依存有無(エディタで要確認 → 移植可否対応表)
- [ ] `AddViewportWidgetContent` の ZOrder と `UUserWidget::AddToViewport` の
      ZOrder オフセット(+10)の関係の実機確認(既定 ZOrder をいくつにするか)
- [ ] スプリットスクリーン/複数 LocalPlayer 時の挙動(現状プラグイン自体が単一想定)
- [ ] `bTickWhenPaused` とウィジェット描画の相互作用(Slate はポーズ非依存なので問題ない見込み)
