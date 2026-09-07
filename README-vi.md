# UseAgent

[English](README.md) | Tiếng Việt

[![CI](https://github.com/thuanlyt/UseAgent/actions/workflows/ci.yml/badge.svg)](https://github.com/thuanlyt/UseAgent/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/thuanlyt/UseAgent?display_name=tag&sort=semver)](https://github.com/thuanlyt/UseAgent/releases/latest)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Lớp evidence và release-assurance nằm trong repository dành cho workflow
> lập trình bằng AI. Supervisor nhẹ là capability tùy chọn khi dự án cần.

![Workflow release-assurance của UseAgent cho dự án lập trình AI](docs-site/assets/useagent-control-plane-hero.webp)

## UseAgent là gì?

UseAgent giữ lại bằng chứng của quá trình lập trình có AI ngay trong
repository đang được thay đổi. Nó ghi provenance của evidence, giới hạn và
sanitize output bền vững, gắn QA với source snapshot, xác minh review evidence
và kiểm tra Git release durability trước quyết định release.

Kết quả là một trail cô đọng, có thể kiểm tra để trả lời các câu hỏi quan
trọng:

- Đã thay đổi gì, và source state nào đã được kiểm tra?
- Evidence là local, live, simulation hay blocked?
- Review và QA có xác minh đúng source chuẩn bị ship không?
- Repository đã sạch và đủ bền vững cho release gate tiếp theo chưa?

UseAgent provider-neutral và trusted-local. Nó bổ sung cho coding runtime,
không cố trở thành coding runtime.

## Phiên bản hiện tại

**v0.1.1 — Distribution & Positioning Maintenance / Bảo trì phân phối và định vị**

v0.1.1 là bản phát hành bảo trì công khai hiện tại. Bản này không thêm
feature set mới: nó làm sạch distribution public và đồng bộ dự án với định vị
release-assurance. Feature set đã được freeze; thay đổi tương lai cần bug cụ
thể, vấn đề bảo mật, evidence từ user bên ngoài hoặc quyết định rõ ràng của
owner.

- [Release notes](https://github.com/thuanlyt/UseAgent/releases/tag/v0.1.1) · [Tất cả bản phát hành](https://github.com/thuanlyt/UseAgent/releases)
- [CHANGELOG](CHANGELOG.md) · [Tài liệu](https://useagent.thuanlyt.id.vn/) · [Hướng dẫn bắt đầu](docs/getting-started.md)

Repository public không đóng gói runtime history của maintainer. `work/` được
`init` tạo local trong project đang được assurance.

## Vì sao dùng UseAgent?

| Vấn đề release-assurance | Cách UseAgent đáp ứng |
| --- | --- |
| Khó audit output của AI về sau | Evidence provenance có kiểu và handover có source anchor |
| Check xanh có thể thuộc về tree cũ | Source-bound QA và freshness check rõ ràng |
| Raw runner output có thể chứa secret | Summary bounded đã sanitize và diagnostic spool local |
| Nhầm “done” với “sẵn sàng release” | Review, QA và Git durability gate tách biệt |
| Công việc dài bị mất context bền vững | Knowledge card, report và checkpoint cô đọng |
| Runtime lập trình AI có workflow khác nhau | Một contract local chung quanh output của chúng |

## Nếu tôi đã dùng Claude Code, Codex, Beads hoặc worktree thì sao?

Các công cụ đó lập kế hoạch và thực thi công việc. UseAgent xác minh evidence
và release state quanh repository sau khi công việc được thực hiện. Nó đứng
bên cạnh các công cụ đó, không bắt chúng từ bỏ planning, subagent, branch hay
worktree management vốn có:

```text
Claude Code / Codex / Beads / worktree
             lập kế hoạch và thực thi
                         ↓
UseAgent xác minh evidence, source identity và release durability
```

UseAgent là lớp bổ sung, không thay thế Beads, Spec Kit, native Claude/Codex
subagent, Git worktree manager hay CI của project.

## UseAgent xác minh điều gì?

- Evidence có provenance được kiểm soát và source anchor có thể lặp lại.
- Runner/QA summary bền vững được giới hạn và sanitize; raw diagnostic mặc định
  chỉ nằm local.
- QA gắn với Git HEAD, source content, dirty-state provenance và QA config.
- Cần review evidence trước khi work item được coi là done.
- Release durability kiểm tra Git cleanliness, untracked file và QA hiện tại
  tách biệt với task completion.
- Quality gate được cấu hình rõ; quyền deploy vẫn thuộc project owner.

## Supervisor nhẹ là capability tùy chọn

Khi project cần supervisor, `$useagent` có thể biến goal ngắn thành workflow hữu
hạn: ghi assumption, tạo work item theo dependency, dispatch assignment, ingest
report, kiểm tra evidence, chạy QA và checkpoint hành động tiếp theo. DAG,
mailbox, role và telemetry vẫn được giữ, nhưng đây là capability điều phối tùy
chọn — không phải identity chính của sản phẩm.

Role là persona của workflow, không phải identity của vendor:

| Role | Trách nhiệm |
| --- | --- |
| `supervisor` | Lập bounded work, review evidence và chọn hành động an toàn tiếp theo |
| `explorer` | Discovery chỉ đọc và source anchor |
| `planner` | Chia goal thành work item có scope |
| `worker` | Implement một scope đã claim và report check |
| `reviewer` | Xác minh diff, regression, security và evidence |
| `release_gate` | Kiểm tra release readiness và operational evidence |

Codex, Claude Code, Google Antigravity và coding agent khác có thể làm worker
khi đọc được contract của repository, chạy được CLI và tôn trọng scope. Xem
[hướng dẫn runtime thực tế](docs/getting-started.md).

## Giám sát có judgment

Supervisor tùy chọn ghi lại ranh giới quyết định, không ghi chain-of-thought
ẩn. Mỗi bounded cycle nên nêu intent, tradeoff, owner, evidence anchor và
next action hoặc điều kiện dừng. Khi marginal value thấp hoặc evidence còn mơ
hồ, supervisor nên dừng và hỏi owner thay vì tạo thêm việc. Cách này giữ điều
phối hữu ích, tôn trọng diminishing returns và ranh giới trusted-local.

## Quick start cho project bên ngoài

Thông thường UseAgent được clone hoặc cài một lần, sau đó trỏ vào repository
muốn kiểm tra. Không dùng checkout source của UseAgent làm application
workspace mặc định.

Yêu cầu: Python 3.11+, Git và một target repository đã tồn tại.

```powershell
git clone https://github.com/thuanlyt/UseAgent.git F:\tools\UseAgent
python F:\tools\UseAgent\tools\useagent.py --root F:\dev\MyProject init
```

`init` tạo local state rỗng tại `F:\dev\MyProject\work`. Nó không copy skill
hoặc ghi đè file project. Để dùng đầy đủ workflow, hãy copy hoặc merge các
file control-plane của UseAgent (`AGENTS.md`, `.agents/skills/`, `knowledge/`,
`tools/useagent.py` và config) vào target repository, giữ nguyên instruction và
source của target. Sau đó chạy:

```powershell
python F:\tools\UseAgent\tools\useagent.py --root F:\dev\MyProject validate
```

Boundary `--root` bao phủ registry, report, evidence, checkpoint và mọi path
đã cấu hình. Path đi ra ngoài boundary sẽ bị từ chối. Nếu đã cài CLI, dùng:

```powershell
python -m pip install --no-deps F:\tools\UseAgent
useagent --root F:\dev\MyProject init
useagent --root F:\dev\MyProject validate
```

Đọc [hướng dẫn bắt đầu](docs/getting-started.md) trước khi đăng ký worker.

## Vòng assurance

Core path dùng được với một agent hoặc nhiều agent:

```text
implement → report evidence → review → source-bound QA → Git durability gate
```

Nếu bật supervision, vòng tùy chọn thêm:

```powershell
python tools/useagent.py supervisor cycle --run-qa
python tools/useagent.py supervisor report --check
```

Worker có thể dùng mailbox/report protocol được tạo sẵn, nhưng project cũng có
thể đặt UseAgent quanh công việc do orchestrator bên ngoài lập kế hoạch. Worker
report không phải release decision; review, QA và durability gate vẫn tách biệt.

## Trust model và ranh giới concurrency

UseAgent được thiết kế cho threat model **trusted-local / trusted-repository**.
Scope và role check là workflow control, không phải OS sandbox, distributed lock
được authenticate hay hệ thống authenticated agent identity.

UseAgent không sở hữu:

- branch, worktree hay process isolation song song;
- provider account, quota hay vendor API launch flag;
- task graph nếu một orchestrator khác đang sở hữu;
- deploy hoặc external mutation.

External orchestrator có thể quản lý branch, worktree, parallel execution và
task graph. UseAgent xác minh repository state sau đó. Shared-folder và
mailbox workflow trong guide supervision là cố ý nhẹ và trusted-local.

## Bản đồ repository và tài liệu

| Path | Mục đích |
| --- | --- |
| `.agents/skills/` | Skill supervisor, context, worker, review và autopilot tùy chọn |
| `.codex/agents/` | Profile Codex theo role, tùy chọn |
| `knowledge/` | Project brief, architecture, contract và decision cô đọng |
| `tools/useagent.py` | Assurance CLI và validator, không dependency |
| `useagent.config.json` | Cấu hình path, QA và production-readiness |
| `work/` | Registry, report, evidence và checkpoint local được tạo sau `init` |
| `docs/` | Tài liệu thao tác, vận hành, architecture và case study chuẩn |
| `docs-site/` | Website tài liệu tĩnh song ngữ, crawlable |
| `tests/` | Regression test standard library và docs-site |

[Case study dogfood OSBlog](docs/case-study-osblog.md) cho thấy workload thật
đã dùng evidence, QA và recovery boundary ra sao. OSBlog là workload và nguồn
evidence, không phải sản phẩm được định vị ở đây.

## Ghi chú đóng gói

Package hiện giữ public entry point ổn định `useagent = tools.useagent:main` và
`packages = ["tools"]`. Top-level package tên chung `tools` có thể collision với
package khác khi cùng import trong một Python environment, dù CLI đã cài và
wheel smoke path vẫn dùng được. Namespace migration là thay đổi compatibility,
nằm ngoài pass freeze này; chỉ nên xem xét khi có evidence install lỗi cụ thể và
quyết định maintenance release rõ ràng.

## Đóng góp và giấy phép

Đóng góp tuân theo [work-item và review contract](CONTRIBUTING.md). Khi báo cáo
vấn đề bảo mật, hãy đọc [SECURITY.md](SECURITY.md). Dự án phát hành theo [MIT
License](LICENSE).

---

## 💖 Support the Project

UseAgent là **miễn phí và mã nguồn mở**. Nếu dự án giúp bạn tiết kiệm thời gian, hãy tặng một ⭐ **Star** — đó là động lực để dự án tiếp tục phát triển và có thêm nhiều skill hơn.

<a href="https://github.com/thuanlyt/UseAgent/stargazers">
  <img src="https://img.shields.io/github/stars/thuanlyt/UseAgent?style=social" alt="GitHub Stars">
</a>

### 🤝 Cộng đồng & Hỗ trợ
- 📖 [Đọc tài liệu](https://useagent.thuanlyt.id.vn/)
- 🐛 [Báo lỗi](https://github.com/thuanlyt/UseAgent/issues)
- 🌐 [Website ThuanLYT](https://thuanlyt.id.vn)

<p align="center"><em>Được xây dựng bằng ❤️ bởi ThuanLYT</em></p>
