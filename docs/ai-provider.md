# AI provider connection

In Kapowarr-AI, open **Settings → AI Provider**. Enter the OpenAI-compatible API
base URL (including its `/v1` prefix when required), model identifier, optional API
key, and a timeout from 5 to 120 seconds. Local HTTP endpoints and container DNS
names are supported. Use an address reachable from the NAS container;
`localhost` refers to that container.

**Test Connection** uses the values currently in the form without saving them.
It sends a small chat-completion prompt and verifies that the model returns a
nonempty text reply. This can consume provider quota. No library files or metadata
are sent. Authentication, rate-limit, endpoint and malformed-response failures
are reported without displaying provider response bodies or credentials.
Transport errors distinguish TLS, DNS, refused connections, connection timeouts
and response timeouts. A response timeout may mean the model is loading or busy;
try increasing the timeout up to 120 seconds. Connection establishment has a
separate 5-second timeout. Reachability from another machine does not establish
NAS connectivity or a successful authenticated model response.
Redirects are not followed; enter the final API URL.

**Save** persists the settings. Saved keys are masked in API responses and the
form; leaving the mask unchanged preserves the key. Clear the field to use a
keyless endpoint. Re-enter the key before testing a different URL: the test will
not forward a saved key to a changed endpoint. Credentials are stored in the
application database, so protect its backups like other application credentials.

Pack Inbox now offers explicit [AI matching suggestions](pack-inbox.md#ai-matching-suggestions-kapowarr-ai).
Saving these settings does not run AI automatically. Chat, automatic downloads
and metadata changes remain outside this slice. Kapowarr's existing import and
naming behavior remains in use.

## Isolated NAS check

1. Update the separate Kapowarr-AI test container after its image build passes.
2. Save the endpoint and model, reload the page, and confirm persistence and key masking.
3. Test the intended model and confirm a successful reply. If it fails, check the
   URL/API prefix, model identifier, provider permissions and NAS network access.
4. Try an invalid model or key and confirm a useful error and usable controls.

Automated tests use mocked providers, not a live AI service. A passing fixture test
is not proof that a particular provider/model combination is compatible.
