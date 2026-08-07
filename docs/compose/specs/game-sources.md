---
feature: game-sources
status: designed
updated: 2026-08-07
---

# 游戏发售多数据源支持

## [S1] Problem

当前游戏发售模块仅用 RAWG API（`collectors/game.py`），需 API Key 且国内不挂代理不可用。需提供用户可自行选择的数据源，解决国内网络可用性。

## [S2] Design

### 数据源

| 源 | key | 国内直连 | 说明 |
|---|---|---|---|
| `rawg` | 需 key | ❌ | 现有实现，全平台数据 |
| `epic` | 免 key | ✅ | Epic 商店 `storefrontLayout` 的 `branded-list-new-releases` 模块，提供游戏名/发售日期/图片 |

> 小黑盒 API 需逆向签名，已验证不可行，不做。

### 配置

新增 `render.game_source`（枚举，默认 `auto`）：

| 值 | 行为 |
|---|---|
| `auto` | 默认：先尝试 `epic`（免 key 国内直连），失败降级 `rawg` |
| `rawg` | 仅用 RAWG（需 key） |
| `epic` | 仅用 Epic（免 key） |

### 架构

- 抽象 `GameSource` 基类，统一输出 `list[dict]`（`{name, released, platforms, image_url}`）
- 每个源一个实现类：`RawgSource`、`EpicSource`
- `GameCollector` 按 `game_source` 选择源；`auto` 模式按序尝试、失败降级
- 源实例化后复用现有 `BaseCollector` 的 `fetch_json`/`_today()`/错误处理

```python
# collectors/game.py 重构
class GameSource(ABC):  # 抽象基类
    async def fetch_upcoming(self, days: int) -> list[dict]: ...

class RawgSource(GameSource): ...   # 现有 RAWG 逻辑抽出
class EpicSource(GameSource): ...   # 新：解析 storefront new-releases

class GameCollector(BaseCollector):
    async def collect(self):
        rawg_key = self.config.external_api.rawg_api_key
        source_order = ...  # 按 game_source 计算
        for source in source_order:  # auto 时逐个尝试
            try:
                games = await source.fetch_upcoming(self._days)
                if games: return ok
            except Exception:
                continue
        return error_result("所有数据源均失败")
```

### EPIC 数据解析

调用 `https://store-site-backend-static-ipv4.ak.epicgames.com/storefrontLayout?locale=zh-CN&country=CN`，取 `branded-list-new-releases` 模块的 `offers`，每项提取：
- `name` = `offer.title`
- `released` = `offer.releaseDate`（取日期部分）
- `platforms` = Epic 商店（PC 为主，可标注）
- `image_url` = `keyImages` 中 `OfferImageWide` 类型的 url

### 错误与降级

- 单源失败记录日志后尝试下一源（`auto`）
- 指定源（`rawg`/`epic`）失败则模块报错（不静默降级，尊重用户选择）
- 封面图仍走现有 `CoverManager` 下载（含 SSRF/大小限制）

## [S3] Out of Scope

- 不加入 IGDB（需 Twitch OAuth，复杂）
- 不逆向小黑盒签名 API
- 不改动其他采集器

## Tasks

- [ ] T1: 抽取 `RawgSource`（现有 game.py 逻辑抽出为独立源类） — acceptance: game.py 结构重构，RAWG 行为不变 (covers: S2)
- [ ] T2: 实现 `EpicSource`（解析 storefront new-releases） — acceptance: 免 key 返回游戏名/发售日期/图片 (covers: S2)
- [ ] T3: 配置 `render.game_source`（auto/rawg/epic）+ 源分派与 auto 降级 — acceptance: 按配置选择源，auto 失败降级 (covers: S2)
- [ ] T4: README 更新（数据源选择说明 + API 申请指南调整） — acceptance: 文档说明 game_source 与各源要求 (covers: S2)
- [ ] T5: 验证 — py_compile + EPIC 源实测返回数据 + auto 降级逻辑 (covers: S2)