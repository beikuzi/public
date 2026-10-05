# Provider integration notes

- trace.moe: official project https://github.com/soruly/trace.moe ; documented API https://soruly.github.io/trace.moe-api/ ; only anime frame/work candidates. Fixed endpoint https://api.trace.moe/search?anilistInfo . Video/thumbnail URLs from responses are never downloaded or embedded.
- SauceNAO: official API page https://saucenao.com/user.php?page=search-api ; fixed endpoint https://saucenao.com/search.php . Requires the caller's existing key and respects reported quota/failures. Similarity is the native 0–100 score, not an attribution probability.
- AnimeTrace (experimental): official docs https://www.animetrace.com/api-docs/ ; fixed GET https://api.animetrace.com/v1/model/list chooses the enabled default model, then POST https://api.animetrace.com/v1/search with file/model/is_multi=1/ai_detect=0. No key in official example; formal pricing and fixed free quotas were not verified. Character/work candidates only.
- Manual routes: https://iqdb.org/ , https://ascii2d.net/ , https://lens.google/ , https://tineye.com/ . Opening these links does not perform a search. Upload manually only if desired.
- Bing Search API is not integrated: the retired API is not a current search backend.

Live availability is distinct from implementation readiness. Offline tests validate mocked provider payloads, never demonstrate live source coverage. The report records an individual adapter's status for every run.
