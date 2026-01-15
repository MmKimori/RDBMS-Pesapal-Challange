(() => {
    const apiBase = '/api/users';

    const form = document.getElementById('user-form');
    const idInput = document.getElementById('user-id');
    const nameInput = document.getElementById('user-name');
    const emailInput = document.getElementById('user-email');
    const resetBtn = document.getElementById('reset-btn');
    const refreshBtn = document.getElementById('refresh-btn');
    const tableBody = document.getElementById('users-table').querySelector('tbody');
    const messageEl = document.getElementById('message');

    function setMessage(text, kind = '') {
        messageEl.textContent = text || '';
        messageEl.className = 'message';
        if (kind) {
            messageEl.classList.add(kind);
        }
    }

    async function fetchJson(url, options = {}) {
        const res = await fetch(url, {
            headers: { 'Content-Type': 'application/json' },
            ...options,
        });
        let body = null;
        try {
            body = await res.json();
        } catch {
            // ignore
        }
        if (!res.ok) {
            const errorMsg = (body && body.error) || res.statusText || 'Request failed';
            throw new Error(errorMsg);
        }
        return body;
    }

    async function loadUsers() {
        try {
            const users = await fetchJson(apiBase);
            tableBody.innerHTML = '';
            users.forEach((u) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${u.id}</td>
                    <td>${u.name}</td>
                    <td>${u.email}</td>
                    <td class="actions-cell">
                        <button type="button" data-action="edit" data-id="${u.id}" class="secondary small">Edit</button>
                        <button type="button" data-action="delete" data-id="${u.id}" class="secondary small">Delete</button>
                    </td>
                `;
                tableBody.appendChild(tr);
            });
        } catch (err) {
            setMessage(err.message, 'error');
        }
    }

    async function upsertUser(evt) {
        evt.preventDefault();
        const id = Number(idInput.value);
        const name = nameInput.value.trim();
        const email = emailInput.value.trim();
        if (!Number.isInteger(id) || !name || !email) {
            setMessage('Please provide a valid id, name and email.', 'error');
            return;
        }
        try {
            // Try update first; if not found, create.
            try {
                await fetchJson(`${apiBase}/${id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ name, email }),
                });
                setMessage('User updated successfully.', 'success');
            } catch (err) {
                // If update fails due to not found, try create
                if (String(err.message).toLowerCase().includes('not found')) {
                    await fetchJson(apiBase, {
                        method: 'POST',
                        body: JSON.stringify({ id, name, email }),
                    });
                    setMessage('User created successfully.', 'success');
                } else {
                    throw err;
                }
            }
            form.reset();
            await loadUsers();
        } catch (err) {
            setMessage(err.message, 'error');
        }
    }

    function onTableClick(evt) {
        const btn = evt.target.closest('button[data-action]');
        if (!btn) return;
        const id = btn.getAttribute('data-id');
        const action = btn.getAttribute('data-action');
        if (!id) return;
        if (action === 'edit') {
            const tr = btn.closest('tr');
            if (!tr) return;
            const cells = tr.querySelectorAll('td');
            idInput.value = cells[0].textContent.trim();
            nameInput.value = cells[1].textContent.trim();
            emailInput.value = cells[2].textContent.trim();
            setMessage('Editing user – make changes and click Save.', 'success');
        } else if (action === 'delete') {
            if (!confirm('Delete this user?')) return;
            deleteUser(Number(id));
        }
    }

    async function deleteUser(id) {
        try {
            await fetchJson(`${apiBase}/${id}`, { method: 'DELETE' });
            setMessage('User deleted.', 'success');
            await loadUsers();
        } catch (err) {
            setMessage(err.message, 'error');
        }
    }

    form.addEventListener('submit', upsertUser);
    resetBtn.addEventListener('click', () => {
        form.reset();
        setMessage('');
    });
    refreshBtn.addEventListener('click', () => {
        setMessage('');
        loadUsers();
    });
    tableBody.addEventListener('click', onTableClick);

    // Initial load
    loadUsers();
})();

