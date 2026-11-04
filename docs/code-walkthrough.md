# Code Walkthrough — study this before your review

Your mentor said you must be able to explain every line. Read the files in this order and
make sure you can answer the questions under each one.

## 1. Follow one request: `POST /api/v1/products`

1. `app/core/middleware.py` — the request enters; a request id is attached; the response is logged on the way out.
2. `app/api/v1/products.py` → `create_product` — FastAPI parses the JSON into `ProductCreate`. If that fails, the service is never called.
3. `app/schemas/product.py` → `ProductCreate` — trimming, lengths, `price > 0`, 2 decimals, strict types, `extra="forbid"`.
4. `app/api/dependencies.py` — builds `ProductService(ProductRepository(session))` for this request.
5. `app/services/product_service.py` → `create` — checks the name is free, builds the entity, saves it, returns a DTO.
6. `app/repositories/product_repository.py` → `find_by_name`, `save` — the only place with SQL.
7. Back in the controller — sets the `Location` header; FastAPI returns 201 with camelCase JSON.

If anything raises, `app/exceptions/handlers.py` turns it into the standard error JSON.

## 2. Questions your mentor is likely to ask

- **Why three layers?** Controllers only speak HTTP, services hold rules and can be unit-tested without a DB, repositories hide SQL. You can swap any layer without touching the others.
- **Why DTOs instead of returning the entity?** The API contract stays stable even if the table changes, and internal columns are never leaked.
- **Where is the duplicate-name rule?** In the service (`_ensure_name_available`) for a clear 409, *and* as a unique index on `lower(name)` in the migration, in case two requests race. `_save` turns that DB error into a 409 too.
- **PUT vs PATCH?** PUT sends the whole product (missing optional fields reset). PATCH uses `model_dump(exclude_unset=True)` so only sent fields change.
- **Why does `ProductPatch.name` have type `NameStr = None` and not `NameStr | None`?** Omitted fields keep the default and are skipped; an explicit `null` is validated against `NameStr` and fails. Only `description` may be null.
- **How do you stop clients setting `id`/timestamps?** They're not in the request DTOs and `extra="forbid"` rejects them. The model generates them (`default=uuid.uuid4`, `default=utcnow`, `onupdate=utcnow`).
- **Why is the 500 handler safe?** It logs the stack trace with `logger.exception` but returns a generic message.
- **Where do settings come from?** `app/core/config.py` reads env vars / `.env`. `DATABASE_URL` has no default, so a missing config fails fast.
- **Why Alembic and not `create_all`?** The schema is versioned and reviewable; the app never creates tables at startup. Tests run the same migration.
- **How is `totalPages` calculated?** `ceil(totalItems / size)`, 0 when empty. Offset is `(page - 1) * size`.
- **Why sort by `id` as well?** So rows with the same price don't swap between pages.

## 3. Practise a live change (the mentor will ask for one)

Try each, then run `pytest`:

1. Allow sorting by `status` → add it to `SORT_COLUMNS` in the repository, add a test.
2. Change the default page size to 20 → controller `Query(10, ...)`, README, tests.
3. Add a `name` partial-search filter → `ProductListQuery`, controller param, repository `ilike`, test.
4. Add a column (e.g. `sku`) → model, new Alembic migration (`alembic revision -m "add sku"`), DTOs, tests.

## 4. Suggested commit history (do it yourself, on a feature branch)

```
chore: project skeleton, .gitignore, README stub
feat: products table migration and entity
feat: create and get-by-id endpoints
feat: list endpoint with pagination, filtering and sorting
feat: put, patch and delete endpoints
feat: global error handler and standard error format
feat: health endpoint and request logging
test: unit tests for product service
test: API tests for all endpoints
docs: README, OpenAPI file, Postman collection
```
