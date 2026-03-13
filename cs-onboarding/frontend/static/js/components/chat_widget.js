(function (global) {
  'use strict';

  if (global.__chatWidgetInitialized) return;
  global.__chatWidgetInitialized = true;

  var root = document.getElementById('chatWidgetRoot');
  if (!root) return;

  var toggleBtn = document.getElementById('chatWidgetToggle');
  var panel = document.getElementById('chatWidgetPanel');
  var closeBtn = document.getElementById('chatWidgetClose');
  var minimizeBtn = document.getElementById('chatWidgetMinimize');
  var newBtn = document.getElementById('chatWidgetNewConversation');
  var newBtnAlt = document.getElementById('chatWidgetNewConversationAlt');
  var conversationList = document.getElementById('chatConversationList');
  var messagesEl = document.getElementById('chatMessages');
  var sendBtn = document.getElementById('chatSendMessage');
  var inputEl = document.getElementById('chatMessageInput');
  var fileInputEl = document.getElementById('chatFileInput');
  var attachFileBtn = document.getElementById('chatAttachFileBtn');
  var attachImageBtn = document.getElementById('chatAttachImageBtn');
  var emojiBtn = document.getElementById('chatEmojiBtn');
  var emojiHost = document.getElementById('chatEmojiPickerHost');
  var attachmentPreviewEl = document.getElementById('chatAttachmentPreview');
  var editBannerEl = document.getElementById('chatEditBanner');
  var cancelEditBtn = document.getElementById('chatCancelEditBtn');
  var badgeEl = document.getElementById('chatWidgetBadge');
  var userSearchInput = document.getElementById('chatUserSearchInput');
  var userSearchResults = document.getElementById('chatUserSearchResults');
  var searchBox = document.getElementById('chatSearchBox');
  var threadTitle = document.getElementById('chatThreadTitle');
  var threadAvatarEl = document.getElementById('chatThreadAvatar');
  var dateLabel = document.getElementById('chatDateLabel');

  var state = {
    open: false,
    activeConversationId: null,
    conversations: [],
    messages: [],
    pollTimer: null,
    searchTimer: null,
    isRefreshing: false,
    stream: null,
    reconnectTimer: null,
    lastRefreshAt: 0,
    context: root.dataset.context || 'onboarding',
    currentUserEmail: (root.dataset.currentUserEmail || '').toLowerCase(),
    currentUserName: root.dataset.currentUserName || root.dataset.currentUserEmail || 'Usuário',
    currentUserPhotoUrl: root.dataset.currentUserPhotoUrl || '',
    pendingAttachment: null,
    editingMessageId: null,
    emojiPicker: null,
  };

  function isOkResponse(payload) {
    return payload && payload.ok;
  }

  async function api(url, options) {
    var res = await fetch(url, Object.assign({
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      }
    }, options || {}));

    var data = await res.json().catch(function () { return { ok: false, error: 'Resposta invalida' }; });
    if (!res.ok || !isOkResponse(data)) {
      throw new Error(data.error || 'Falha ao carregar chat');
    }
    return data;
  }

  function escapeHtml(text) {
    return (text || '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function isImageAttachment(attachment) {
    var ct = String((attachment && attachment.attachment_content_type) || '').toLowerCase();
    return ct.startsWith('image/');
  }

  function renderAttachment(message) {
    var url = message.attachment_url;
    if (!url) return '';

    var name = message.attachment_name || 'anexo';
    var isImage = isImageAttachment(message);
    if (isImage) {
      return [
        '<a href="' + escapeHtml(url) + '" target="_blank" rel="noopener noreferrer">',
        '<img class="chat-attachment-image" src="' + escapeHtml(url) + '" alt="' + escapeHtml(name) + '">',
        '</a>'
      ].join('');
    }

    return [
      '<a class="chat-attachment-link" href="' + escapeHtml(url) + '" target="_blank" rel="noopener noreferrer">',
      '<i class="bi bi-file-earmark-pdf"></i>',
      '<span>' + escapeHtml(name) + '</span>',
      '</a>'
    ].join('');
  }

  function clearPendingAttachment() {
    state.pendingAttachment = null;
    if (attachmentPreviewEl) {
      attachmentPreviewEl.innerHTML = '';
      attachmentPreviewEl.classList.add('d-none');
    }
    if (fileInputEl) {
      fileInputEl.value = '';
    }
  }

  function clearEditState() {
    state.editingMessageId = null;
    if (editBannerEl) {
      editBannerEl.classList.add('d-none');
    }
  }

  function insertTextAtCursor(input, text) {
    if (!input) return;
    var start = typeof input.selectionStart === 'number' ? input.selectionStart : input.value.length;
    var end = typeof input.selectionEnd === 'number' ? input.selectionEnd : input.value.length;
    var value = input.value || '';
    input.value = value.slice(0, start) + text + value.slice(end);
    var cursor = start + text.length;
    input.focus();
    try {
      input.selectionStart = cursor;
      input.selectionEnd = cursor;
    } catch (e) {
      // noop
    }
  }

  function startEditMode(messageId) {
    var current = state.messages.find(function (m) { return Number(m.id) === Number(messageId); });
    if (!current) return;
    if (current.deleted_at) return;

    state.editingMessageId = Number(messageId);
    if (editBannerEl) {
      editBannerEl.classList.remove('d-none');
    }
    if (inputEl) {
      inputEl.value = current.content || '';
      inputEl.focus();
      try {
        inputEl.selectionStart = inputEl.value.length;
        inputEl.selectionEnd = inputEl.value.length;
      } catch (e) {
        // noop
      }
    }
  }

  function initEmojiPicker() {
    if (!emojiBtn || !inputEl || !emojiHost) return;
    if (!global.picmo || typeof global.picmo.createPicker !== 'function') return;
    try {
      state.emojiPicker = global.picmo.createPicker({
        rootElement: emojiHost,
        theme: 'dark',
        showPreview: true,
        showRecents: true,
        showSearch: true
      });

      state.emojiPicker.addEventListener('emoji:select', function (selection) {
        if (!selection) return;
        var chosen = selection.emoji || null;
        if (!chosen) return;
        var value = chosen.emoji || chosen;
        insertTextAtCursor(inputEl, value);
      });

      emojiBtn.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        emojiHost.classList.toggle('d-none');
      });
    } catch (error) {
      console.warn('Emoji picker init failed:', error && error.message ? error.message : error);
    }
  }

  function showAttachmentPreview(attachment) {
    if (!attachmentPreviewEl) return;
    if (!attachment || !attachment.attachment_url) {
      clearPendingAttachment();
      return;
    }

    var isImage = isImageAttachment(attachment);
    var icon = isImage ? 'bi-image' : 'bi-file-earmark-pdf';
    var previewThumb = isImage
      ? '<img class="chat-attachment-preview-thumb" src="' + escapeHtml(attachment.attachment_url) + '" alt="' + escapeHtml(attachment.attachment_name || 'imagem') + '">'
      : '<span class="chat-attachment-preview-thumb d-inline-flex align-items-center justify-content-center"><i class="bi ' + icon + '"></i></span>';

    attachmentPreviewEl.innerHTML = [
      '<div class="chat-attachment-preview-main">',
      previewThumb,
      '<div class="chat-attachment-preview-name">' + escapeHtml(attachment.attachment_name || 'arquivo') + '</div>',
      '</div>',
      '<button type="button" id="chatAttachmentRemoveBtn" class="chat-attachment-remove" title="Remover anexo"><i class="bi bi-x-lg"></i></button>'
    ].join('');
    attachmentPreviewEl.classList.remove('d-none');
  }

  function getInitials(name) {
    var normalized = String(name || '').trim();
    if (!normalized) return '??';
    var parts = normalized.split(/\s+/).filter(Boolean);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0].charAt(0) + parts[1].charAt(0)).toUpperCase();
  }

  function renderAvatarHtml(photoUrl, name, className) {
    var cls = className || 'chat-avatar';
    if (photoUrl) {
      return '<img class="' + cls + '" src="' + escapeHtml(photoUrl) + '" alt="' + escapeHtml(name || 'avatar') + '">';
    }
    return '<span class="' + cls + '">' + escapeHtml(getInitials(name)) + '</span>';
  }

  function formatMessageDate(value) {
    if (!value) return '';
    var d = new Date(value);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }

  function formatConversationTime(value) {
    if (!value) return '';
    var d = new Date(value);
    if (Number.isNaN(d.getTime())) return '';

    var now = new Date();
    var sameDay = d.toDateString() === now.toDateString();
    if (sameDay) {
      return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    }

    var yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    if (d.toDateString() === yesterday.toDateString()) {
      return 'Ontem';
    }

    return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
  }

  function getDateLabel(messages) {
    var now = new Date();
    var dateRef = messages && messages.length ? new Date(messages[messages.length - 1].created_at) : now;
    if (Number.isNaN(dateRef.getTime())) dateRef = now;

    var sameDay = dateRef.toDateString() === now.toDateString();
    var base = sameDay ? 'HOJE' : dateRef.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    return base;
  }

  function isNearBottom(container) {
    if (!container) return true;
    var threshold = 56;
    var distance = container.scrollHeight - container.scrollTop - container.clientHeight;
    return distance <= threshold;
  }

  function scrollMessagesToBottom() {
    if (!messagesEl) return;
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function updateBadge() {
    var unread = state.conversations.reduce(function (acc, c) {
      return acc + Number(c.unread_count || 0);
    }, 0);

    if (!badgeEl) return;
    badgeEl.textContent = unread > 99 ? '99+' : String(unread);
    badgeEl.classList.toggle('d-none', unread === 0);
  }

  function updateThreadHeader() {
    if (!threadTitle) return;
    var current = state.conversations.find(function (item) {
      return Number(item.id) === Number(state.activeConversationId);
    });
    var title = current ? (current.other_user_name || current.other_user_email || 'Chat Interno') : 'Chat Interno';
    threadTitle.textContent = title;
    if (threadAvatarEl) {
      threadAvatarEl.outerHTML = renderAvatarHtml(
        current ? current.other_user_photo_url : null,
        title,
        'chat-thread-avatar'
      ).replace('class="chat-thread-avatar"', 'id="chatThreadAvatar" class="chat-thread-avatar"');
      threadAvatarEl = document.getElementById('chatThreadAvatar');
    }
  }

  function renderConversations() {
    if (!conversationList) return;
    if (!state.conversations.length) {
      conversationList.innerHTML = '<div class="chat-empty">Sem conversas ainda.</div>';
      updateThreadHeader();
      return;
    }

    conversationList.innerHTML = state.conversations.map(function (item) {
      var isActive = Number(item.id) === Number(state.activeConversationId);
      var unread = Number(item.unread_count || 0);
      var name = item.other_user_name || item.other_user_email || 'Conversa';
      return [
        '<button type="button" class="chat-conversation-item ' + (isActive ? 'is-active' : '') + '" data-conversation-id="' + item.id + '">',
          '<div class="chat-conversation-top">',
            '<div class="chat-conversation-left">',
              renderAvatarHtml(item.other_user_photo_url, name, 'chat-avatar'),
              '<span class="chat-conversation-name">' + escapeHtml(name) + '</span>',
            '</div>',
            '<span class="chat-conversation-time">' + escapeHtml(formatConversationTime(item.last_message_at || item.updated_at)) + '</span>',
          '</div>',
          '<div class="chat-conversation-preview">' + escapeHtml(item.last_message || 'Inicie a conversa...') + '</div>',
          unread > 0 ? '<span class="badge text-bg-primary" style="margin-left:36px;margin-top:4px;">' + unread + '</span>' : '',
        '</button>'
      ].join('');
    }).join('');

    updateThreadHeader();
  }

  function renderMessages() {
    if (!messagesEl) return;

    if (!state.activeConversationId) {
      messagesEl.innerHTML = '<div class="chat-empty">Selecione uma conversa.</div>';
      if (dateLabel) dateLabel.textContent = 'HOJE';
      return;
    }

    if (!state.messages.length) {
      messagesEl.innerHTML = '<div class="chat-empty">Sem mensagens nesta conversa.</div>';
      if (dateLabel) dateLabel.textContent = 'HOJE';
      return;
    }

    var ordered = state.messages.slice().reverse();

    messagesEl.innerHTML = ordered.map(function (msg) {
      var mine = String(msg.sender_email || '').toLowerCase() === state.currentUserEmail;
      var isDeleted = Boolean(msg.deleted_at);
      var isEdited = Boolean(msg.edited_at);
      var readClass = msg.read_by_recipient ? 'is-read' : '';
      var incomingAvatar = renderAvatarHtml(msg.sender_photo_url, msg.sender_name || msg.sender_email || 'Usuário', 'chat-message-avatar');
      var myAvatar = renderAvatarHtml(state.currentUserPhotoUrl, state.currentUserName, 'chat-message-avatar');

      return [
        '<div class="chat-message-row ' + (mine ? 'mine' : '') + '">',
          !mine ? incomingAvatar : '',
          '<div class="chat-message ' + (mine ? 'mine' : '') + ' ' + (isDeleted ? 'is-deleted' : '') + '">',
          '<div class="chat-message-meta">',
            '<span>' + escapeHtml(mine ? formatMessageDate(msg.created_at) : (msg.sender_name || 'Usuário') + ' • ' + formatMessageDate(msg.created_at)) + '</span>',
            mine ? '<span class="chat-message-check ' + readClass + '"><i class="bi bi-check2-all"></i></span>' : '',
          '</div>',
          '<div class="chat-message-content">' + escapeHtml(msg.content || '') + '</div>',
          renderAttachment(msg),
          '<div class="chat-message-foot">',
            isEdited && !isDeleted ? '<span class="chat-message-edited">editada</span>' : '',
            mine && !isDeleted ? '<button type="button" class="chat-message-btn" data-edit-id="' + msg.id + '" title="Editar"><i class="bi bi-pencil-square"></i></button>' : '',
            mine && !isDeleted ? '<button type="button" class="chat-message-btn chat-message-btn-danger" data-delete-id="' + msg.id + '" title="Excluir"><i class="bi bi-trash3"></i></button>' : '',
          '</div>',
          '</div>',
          mine ? myAvatar : '',
        '</div>'
      ].join('');
    }).join('');

    if (dateLabel) {
      dateLabel.textContent = getDateLabel(ordered);
    }
  }

  function renderSearchResults(items) {
    if (!userSearchResults) return;
    if (!items || !items.length) {
      userSearchResults.innerHTML = '';
      return;
    }

    userSearchResults.innerHTML = items.map(function (item) {
      return [
        '<button type="button" class="chat-user-search-item" data-user-email="' + escapeHtml(item.email) + '">',
        '<div><strong>' + escapeHtml(item.nome || item.email) + '</strong></div>',
        '<div class="text-muted small">' + escapeHtml(item.email) + '</div>',
        '</button>'
      ].join('');
    }).join('');
  }

  async function refreshConversations() {
    var data = await api('/chat/api/conversations');
    state.conversations = data.items || [];

    if (!state.activeConversationId && state.conversations.length) {
      state.activeConversationId = state.conversations[0].id;
    }

    renderConversations();
    updateBadge();
  }

  async function refreshMessages(options) {
    var opts = options || {};
    if (!state.activeConversationId) {
      renderMessages();
      return;
    }

    var shouldAutoScroll = Boolean(opts.forceScroll) || isNearBottom(messagesEl);

    var data = await api('/chat/api/messages?conversation_id=' + encodeURIComponent(state.activeConversationId));
    state.messages = data.items || [];
    renderMessages();
    if (shouldAutoScroll) {
      scrollMessagesToBottom();
    }

    await api('/chat/api/conversations/' + encodeURIComponent(state.activeConversationId) + '/read', {
      method: 'POST',
      body: JSON.stringify({})
    });
  }

  async function refreshAll() {
    var nowTs = Date.now();
    if (nowTs - state.lastRefreshAt < 1200) return;
    if (state.isRefreshing) return;
    state.isRefreshing = true;
    state.lastRefreshAt = nowTs;

    try {
      await refreshConversations();
      if (state.open) {
        await refreshMessages();
      }
    } catch (err) {
      console.warn('Chat refresh failed:', err && err.message ? err.message : err);
    } finally {
      state.isRefreshing = false;
    }
  }

  async function uploadAttachment(file) {
    if (!file) return null;

    var formData = new FormData();
    formData.append('file', file);

    var response = await fetch('/api/upload/comment-attachment', {
      method: 'POST',
      body: formData,
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });

    var data = await response.json().catch(function () {
      return { ok: false, error: 'Falha no upload' };
    });
    if (!response.ok || !data.ok) {
      throw new Error(data.error || 'Falha ao enviar arquivo');
    }

    var attachment = {
      attachment_url: data.attachment_url || data.image_url,
      attachment_name: data.filename || file.name || 'arquivo',
      attachment_content_type: data.content_type || file.type || 'application/octet-stream'
    };
    state.pendingAttachment = attachment;
    showAttachmentPreview(attachment);
    return attachment;
  }

  async function sendMessage() {
    if (!state.activeConversationId || !inputEl) return;

    var content = (inputEl.value || '').trim();
    if (state.editingMessageId) {
      if (!content) return;
      await api('/chat/api/messages/' + encodeURIComponent(state.editingMessageId), {
        method: 'PUT',
        body: JSON.stringify({ content: content })
      });
      inputEl.value = '';
      clearEditState();
      await refreshAll();
      return;
    }

    if (!content && !state.pendingAttachment) return;

    await api('/chat/api/messages', {
      method: 'POST',
      body: JSON.stringify({
        conversation_id: state.activeConversationId,
        content: content,
        attachment_url: state.pendingAttachment ? state.pendingAttachment.attachment_url : null,
        attachment_name: state.pendingAttachment ? state.pendingAttachment.attachment_name : null,
        attachment_content_type: state.pendingAttachment ? state.pendingAttachment.attachment_content_type : null
      })
    });

    inputEl.value = '';
    if (emojiHost) {
      emojiHost.classList.add('d-none');
    }
    clearPendingAttachment();
    clearEditState();
    await refreshConversations();
    await refreshMessages({ forceScroll: true });
  }

  async function editMessage(messageId) {
    startEditMode(messageId);
  }

  async function deleteMessage(messageId) {
    var ok = true;
    if (global.ConfirmDialog && typeof global.ConfirmDialog.show === 'function') {
      ok = await global.ConfirmDialog.show({
        title: 'Confirmar exclusao',
        message: 'Tem certeza que deseja excluir esta mensagem?',
        confirmText: 'Excluir',
        cancelText: 'Cancelar',
        type: 'danger',
        alertLabel: 'Atencao! Esta acao nao pode ser desfeita.'
      });
    } else {
      ok = global.confirm('Excluir esta mensagem?');
    }
    if (!ok) return;

    await api('/chat/api/messages/' + encodeURIComponent(messageId), {
      method: 'DELETE'
    });

    await refreshAll();
  }

  async function createConversation(otherEmail) {
    await api('/chat/api/conversations', {
      method: 'POST',
      body: JSON.stringify({ other_user_email: otherEmail })
    });

    if (userSearchInput) userSearchInput.value = '';
    if (userSearchResults) userSearchResults.innerHTML = '';

    await refreshConversations();
    if (state.conversations.length) {
      var conv = state.conversations.find(function (c) {
        return (c.other_user_email || '').toLowerCase() === String(otherEmail).toLowerCase();
      });
      if (conv) {
        state.activeConversationId = conv.id;
      }
      await refreshMessages();
    }
  }

  async function searchUsers(term) {
    if (!term || term.length < 2) {
      renderSearchResults([]);
      return;
    }

    var data = await api('/chat/api/users?q=' + encodeURIComponent(term));
    renderSearchResults(data.items || []);
  }

  function connectStream() {
    if (typeof EventSource === 'undefined') {
      startPolling();
      return;
    }

    if (state.reconnectTimer) {
      global.clearTimeout(state.reconnectTimer);
      state.reconnectTimer = null;
    }

    if (state.stream) {
      state.stream.close();
    }

    state.stream = new EventSource('/chat/api/stream', { withCredentials: true });
    state.stream.onopen = function () {
      stopPolling();
    };
    state.stream.addEventListener('sync', function () {
      refreshAll();
    });

    state.stream.onerror = function () {
      try {
        state.stream.close();
      } catch (e) {
        console.warn('Failed closing chat stream', e);
      }
      state.stream = null;
      startPolling();
      if (state.reconnectTimer) {
        global.clearTimeout(state.reconnectTimer);
      }
      state.reconnectTimer = global.setTimeout(function () {
        state.reconnectTimer = null;
        connectStream();
      }, 2500);
    };
  }

  function setOpen(open) {
    state.open = open;
    if (!panel) return;
    panel.classList.toggle('is-open', open);
  }

  function startPolling() {
    if (state.pollTimer) clearInterval(state.pollTimer);
    state.pollTimer = global.setInterval(refreshAll, 15000);
  }

  function stopPolling() {
    if (!state.pollTimer) return;
    global.clearInterval(state.pollTimer);
    state.pollTimer = null;
  }

  function toggleSearch() {
    if (!searchBox) return;
    searchBox.classList.toggle('d-none');
    if (!searchBox.classList.contains('d-none') && userSearchInput) {
      userSearchInput.focus();
    }
  }

  function wireEvents() {
    if (toggleBtn) {
      toggleBtn.addEventListener('click', async function () {
        setOpen(!state.open);
        if (state.open) {
          await refreshAll();
        }
      });
    }

    if (closeBtn) closeBtn.addEventListener('click', function () { setOpen(false); });
    if (minimizeBtn) minimizeBtn.addEventListener('click', function () { setOpen(false); });

    if (newBtn) newBtn.addEventListener('click', toggleSearch);
    if (newBtnAlt) newBtnAlt.addEventListener('click', toggleSearch);

    if (conversationList) {
      conversationList.addEventListener('click', async function (event) {
        var target = event.target;
        if (!(target instanceof Element)) return;
        var btn = target.closest('[data-conversation-id]');
        if (!btn) return;

        state.activeConversationId = btn.getAttribute('data-conversation-id');
        renderConversations();
        await refreshMessages({ forceScroll: true });
        await refreshConversations();
      });
    }

    if (messagesEl) {
      messagesEl.addEventListener('click', function (event) {
        var target = event.target;
        if (!(target instanceof Element)) return;

        var editBtn = target.closest('[data-edit-id]');
        if (editBtn) {
          var editId = editBtn.getAttribute('data-edit-id');
          if (editId) {
            editMessage(editId).catch(function (err) {
              console.warn('Edit message failed:', err && err.message ? err.message : err);
            });
          }
          return;
        }

        var deleteBtn = target.closest('[data-delete-id]');
        if (deleteBtn) {
          var deleteId = deleteBtn.getAttribute('data-delete-id');
          if (deleteId) {
            deleteMessage(deleteId).catch(function (err) {
              console.warn('Delete message failed:', err && err.message ? err.message : err);
            });
          }
        }
      });
    }

    if (sendBtn) {
      sendBtn.addEventListener('click', function () {
        sendMessage().catch(function (err) {
          console.warn('Send message failed:', err && err.message ? err.message : err);
        });
      });
    }

    if (inputEl) {
      inputEl.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && state.editingMessageId) {
          event.preventDefault();
          clearEditState();
          inputEl.value = '';
          return;
        }
        if (event.key === 'Enter' && !event.shiftKey) {
          event.preventDefault();
          sendMessage().catch(function (err) {
            console.warn('Send message failed:', err && err.message ? err.message : err);
          });
        }
      });

      inputEl.addEventListener('paste', function (event) {
        var items = event.clipboardData && event.clipboardData.items ? event.clipboardData.items : [];
        for (var i = 0; i < items.length; i += 1) {
          var item = items[i];
          if (!item || !item.type || item.type.indexOf('image/') !== 0) continue;
          var file = item.getAsFile();
          if (!file) continue;
          event.preventDefault();
          uploadAttachment(file).catch(function (err) {
            console.warn('Paste upload failed:', err && err.message ? err.message : err);
          });
          break;
        }
      });
    }

    if (attachFileBtn) {
      attachFileBtn.addEventListener('click', function () {
        if (!fileInputEl) return;
        fileInputEl.setAttribute('accept', 'image/png,image/jpeg,image/jpg,image/gif,image/webp,application/pdf');
        fileInputEl.click();
      });
    }

    if (attachImageBtn) {
      attachImageBtn.addEventListener('click', function () {
        if (!fileInputEl) return;
        fileInputEl.setAttribute('accept', 'image/png,image/jpeg,image/jpg,image/gif,image/webp');
        fileInputEl.click();
      });
    }

    if (fileInputEl) {
      fileInputEl.addEventListener('change', function () {
        var file = fileInputEl.files && fileInputEl.files[0] ? fileInputEl.files[0] : null;
        if (!file) return;
        uploadAttachment(file).catch(function (err) {
          console.warn('Attachment upload failed:', err && err.message ? err.message : err);
        });
      });
    }

    if (attachmentPreviewEl) {
      attachmentPreviewEl.addEventListener('click', function (event) {
        var target = event.target;
        if (!(target instanceof Element)) return;
        if (!target.closest('#chatAttachmentRemoveBtn')) return;
        clearPendingAttachment();
      });
    }

    if (cancelEditBtn) {
      cancelEditBtn.addEventListener('click', function () {
        clearEditState();
      });
    }

    if (userSearchInput) {
      userSearchInput.addEventListener('input', function () {
        var value = (userSearchInput.value || '').trim();
        if (state.searchTimer) clearTimeout(state.searchTimer);
        state.searchTimer = global.setTimeout(function () {
          searchUsers(value).catch(function (err) {
            console.warn('User search failed:', err && err.message ? err.message : err);
          });
        }, 280);
      });
    }

    if (userSearchResults) {
      userSearchResults.addEventListener('click', function (event) {
        var target = event.target;
        if (!(target instanceof Element)) return;
        var btn = target.closest('[data-user-email]');
        if (!btn) return;

        var email = btn.getAttribute('data-user-email');
        if (!email) return;

        createConversation(email).catch(function (err) {
          console.warn('Create conversation failed:', err && err.message ? err.message : err);
        });
      });
    }

    document.addEventListener('click', function (event) {
      if (!emojiHost || emojiHost.classList.contains('d-none')) return;
      var target = event.target;
      if (!(target instanceof Element)) return;
      if (target.closest('#chatEmojiBtn') || target.closest('#chatEmojiPickerHost')) return;
      emojiHost.classList.add('d-none');
    });

  }

  function init() {
    wireEvents();
    initEmojiPicker();
    refreshAll();
    connectStream();
    global.addEventListener('beforeunload', function () {
      if (state.stream) {
        try {
          state.stream.close();
        } catch (e) {
          // noop
        }
        state.stream = null;
      }
      stopPolling();
      if (state.reconnectTimer) {
        global.clearTimeout(state.reconnectTimer);
        state.reconnectTimer = null;
      }
    });
  }

  init();
})(typeof window !== 'undefined' ? window : this);

