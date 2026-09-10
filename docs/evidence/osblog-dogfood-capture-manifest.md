# OSBlog dogfood capture manifest

> Evidence freeze: 2026-09-06. This manifest records what exists, what is
> publishable and what must not be promoted. It does not create a new capture.

## Privacy and provenance rule

Only an artifact whose source, content and privacy boundary are known may be
called product media. A valid file or a successful encoder is not enough. Raw
Cap projects, browser profiles, test recordings and screenshots remain local
unless a human reviews their visible content.

## Curated artifacts

| Artifact | Source and status | Public use |
| --- | --- | --- |
| `public/media/osblog-cap-demo.gif` | Committed in OSBlog at `b8ce741`; SHA-256 `78EB7925AEFD3BE064E4D78B72EA6A4146203823AE143D2042F1916B5684077C`; 374,173 bytes. [`docs/media.md`](https://github.com/thuanlyt/osblog/blob/main/docs/media.md) and UA-0040 describe it as a Cap capture of public OSBlog routes. | **Approved existing product preview.** [Live GIF](https://osblog.thuanlyt.id.vn/media/osblog-cap-demo.gif) |
| `public/media/osblog-cap-demo.mp4` | Committed in OSBlog at `b8ce741`; SHA-256 `B8CBFA963990B97C07E97CB0B0B19C9CB410C8BE49C7E8917148C8B89C2AF01C`; 15,456,695 bytes. The MP4 is the higher-quality companion to the GIF. | **Approved existing product video.** [Live MP4](https://osblog.thuanlyt.id.vn/media/osblog-cap-demo.mp4) |

The live route/content smoke for both Vercel aliases is recorded in
[`work/evidence/ops-recovery-drill.md`](https://github.com/thuanlyt/osblog/blob/main/work/evidence/ops-recovery-drill.md)
and the release report. The media is evidence from the earlier verified
capture; this closeout does not claim a new Brave or Cap invocation.

## Local-only candidates

These files were found in the OSBlog worktree but are not copied into ReleaseWitness
or promoted as public media:

| Candidate | Classification | Handling |
| --- | --- | --- |
| `test-results/home-desktop.png` | Browser QA screenshot | Keep local until visible-content/privacy review; it is test evidence, not a polished product claim. |
| `test-results/article-desktop.png` | Browser QA screenshot | Same rule; link from an evidence report only if the exact run and visible content are reviewed. |
| `test-results/docs-mobile.png` | Responsive/docs screenshot | Useful for a future visual case-study panel after review; not currently public. |
| `test-results/editor-desktop.png` | Admin/editor screenshot | Higher privacy risk because admin UI may expose operator context; do not publish without a fresh sanitized review. |
| `tests/browser/playwright-report/data/*.webm` | Automated browser recordings | Verification artifacts; do not present as the curated Cap walkthrough. |
| `draft/osblog-cap-demo-20260905.cap` | New Cap project | **Blocked.** Cap validation passed, but content could not be verified as OSBlog because the requested Brave window was not exposed and Cap reported no browser windows. |

The blocked result is supported by
[`UA-0086`](https://github.com/thuanlyt/osblog/blob/main/work/reports/inbox/UA-0086-20260905T154011Z-61f28d.md):
`cap doctor` and project validation passed, but no MP4/GIF promotion was
performed. Do not infer content from filenames.

## What is deliberately excluded

- Raw Cap projects and their extracted segments.
- Browser profiles, extension assets and cookies.
- Screenshots whose visible content has not been reviewed.
- Any file containing an admin email, password, session token, environment
  value, database URL or private customer data.
- The ReleaseWitness workflow animation under `draft/`: it is a labeled simulation,
  not OSBlog evidence.

## Re-capture checklist

If an exposed browser/Cap path becomes available, use a new bounded task and
record:

1. The exact public URL and the Vercel alias being shown.
2. The Cap target/window identifier and capture start/stop time.
3. A short route sequence: public home → docs → published article; do not open
   admin screens unless the frame is sanitized.
4. Cap project validation output and media magic/type/size checks.
5. A human-visible privacy review before copying exports to `public/media`.
6. The final SHA-256 values and the exact README/docs links.

Never retry the blocked capture merely to manufacture a new artifact for this
case study. The existing GIF/MP4 are sufficient product media; the blocked
attempt is itself useful workflow evidence.

## Tóm tắt tiếng Việt

Manifest này phân biệt media thật đã được kiểm chứng với file chỉ tồn tại trên
đĩa. GIF và MP4 trong `public/media/` của OSBlog đã commit, có hash và được
document là Cap capture của các route public; chúng được phép dùng làm media
hiện tại.

Ảnh trong `test-results/`, file `.webm` của Playwright và raw Cap project chỉ
là artifact local. Capture mới UA-0086 bị block vì Cap không thấy browser target
Brave và nội dung không xác minh được là OSBlog, nên không export/promote.

Không được đưa secret, cookie, credential, profile trình duyệt hoặc màn hình
admin chưa sanitize vào media public. Nếu sau này có browser target hợp lệ,
hãy tạo task mới có bounded capture, route rõ ràng, privacy review và hash
cuối cùng.
