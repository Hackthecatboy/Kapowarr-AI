usingApiKey().then(async apiKey => {
    const form = document.querySelector('#ai-settings-form');
    const status = document.querySelector('#ai-status');
    const save = document.querySelector('#ai-save');
    const test = document.querySelector('#ai-test');
    const fields = Object.fromEntries(['base_url', 'api_key', 'model', 'timeout'].map(
        name => ['ai_' + name, document.querySelector('#ai-' + name.replaceAll('_', '-'))]));
    let busy = false;
    function fill(values) {
        for (const [name, field] of Object.entries(fields)) field.value = values[name];
    }
    async function errorMessage(error) {
        try {
            const data = await error.json();
            if (data.error === 'InvalidKeyValue') return String(data.result.value);
        } catch (_) {}
        return 'Request failed. Check the connection to Kapowarr and try again.';
    }
    async function run(testOnly) {
        if (busy || !form.reportValidity()) return;
        busy = true;
        save.disabled = test.disabled = true;
        for (const field of Object.values(fields)) field.disabled = true;
        status.textContent = testOnly ? 'Testing model connection…' : 'Saving…';
        status.classList.remove('error');
        const data = Object.fromEntries(Object.entries(fields).map(([name, field]) =>
            [name, name === 'ai_timeout' ? Number(field.value) : field.value]));
        try {
            const response = await sendAPI(testOnly ? 'POST' : 'PUT', testOnly ? '/ai/test' : '/settings', apiKey, {}, data);
            const result = (await response.json()).result;
            if (testOnly) {
                status.textContent = result.message;
                status.classList.toggle('error', !result.success);
            } else {
                fill(result);
                status.textContent = 'Settings saved.';
            }
        } catch (error) {
            status.textContent = await errorMessage(error);
            status.classList.add('error');
        } finally {
            busy = false;
            save.disabled = test.disabled = false;
            for (const field of Object.values(fields)) field.disabled = false;
        }
    }
    form.onsubmit = event => { event.preventDefault(); run(false); };
    test.onclick = () => run(true);
    try {
        fill((await fetchAPI('/settings', apiKey)).result);
        save.disabled = test.disabled = false;
    } catch (error) {
        status.textContent = await errorMessage(error);
        status.classList.add('error');
    }
});
