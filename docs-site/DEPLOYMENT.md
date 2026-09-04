# UseAgent Docs hosting runbook

This site is a static output under `docs-site/`. Hosting is deliberately a
separate gate from local content work.

## Vercel preview

1. Import `thuanlyt/UseAgent` into Vercel.
2. Set the project root directory to `docs-site`.
3. Use the Other/static framework preset. The checked-in `vercel.json` uses
   `python3 build.py --output dist` and publishes `dist`.
4. Create a Preview Deployment from the branch under review.
5. Check every route, the EN/VI language paths, keyboard navigation, search
   behavior, mobile widths (375px and 768px) and the browser console before
   promoting anything to Production.

Vercel's Git integration creates preview deployments for branches and pull
requests. Keep the first deployment preview-only until visual QA passes:
[Vercel for GitHub](https://vercel.com/docs/git/vercel-for-github).

## Custom domain gate

Do not guess or preconfigure a domain. The operator must supply the exact
hostname and confirm that it is the intended production domain.

1. Add the exact hostname in Vercel and copy the DNS records Vercel presents.
2. In Cloudflare, add only those records to the correct zone. Keep the proxy
   mode and TTL consistent with the Vercel instructions.
3. Wait for Vercel domain verification and HTTPS issuance.
4. Re-run route, security-header and canonical/metadata checks on the final
   hostname.

References: [Vercel custom domains](https://vercel.com/docs/domains/set-up-custom-domain)
and [Cloudflare DNS records](https://developers.cloudflare.com/dns/manage-dns-records/how-to/create-dns-records/).

## Search and sharing gate

The confirmed primary origin is `https://useagent.thuanlyt.id.vn/`. Indexable
pages publish absolute canonical and language-alternate links for that origin;
`robots.txt` points crawlers to `sitemap.xml`, which lists the five indexable
routes. Treat the primary origin as the only SEO source of truth and keep the
`vercel.app` hostname as a deployment fallback.

## Rollback

- If a preview is wrong, delete or abandon the preview; do not touch DNS.
- If production is wrong, promote the last known-good Vercel deployment, then
  open a follow-up task with the failed evidence.
- If the source is wrong, revert the offending Git commit through the normal
  review process and let CI rebuild the next preview.
- Record the deployment URL, commit SHA, issue and rollback decision in the
  supervisor report before continuing autopilot.

No environment secret is needed for this static site. UseAgent must not store
Cloudflare or Vercel tokens in the repository.

## Local preview evidence

```powershell
python docs-site/build.py --check-only
python docs-site/build.py --output dist
python -m http.server 4173 --directory docs-site/dist
```

The local preview is a release rehearsal, not proof that a remote deployment or
DNS change succeeded.

## Tiếng Việt

Deploy được tách thành gate riêng. Trước tiên tạo Preview trên Vercel với root
`docs-site`, kiểm tra đủ route, EN/VI, responsive, keyboard và console. Chỉ khi
có hostname production chính xác do người dùng cung cấp mới thêm domain và DNS.
Không đoán domain, không lưu token trong repository. Khi có lỗi, promote
deployment Vercel cuối cùng còn tốt hoặc revert commit, rồi ghi URL/SHA/evidence
vào `work/SUPERVISOR_REPORT.md`.

Hostname SEO chính đã xác nhận là `https://useagent.thuanlyt.id.vn/`. Các trang
được index dùng canonical tuyệt đối và alternate EN/VI về hostname này;
`robots.txt` trỏ tới `sitemap.xml` gồm năm route indexable. Hostname
`vercel.app` chỉ là fallback của deployment.
