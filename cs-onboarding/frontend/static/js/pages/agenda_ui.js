document.addEventListener('DOMContentLoaded', function() {
    const HOUR_HEIGHT = 80;  // px per hour
    const START_HOUR = 8;    // grid starts at 08:00

    const config = window.agendaConfig || {};
    const events = window.agendaEvents || [];

    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const tzEl = document.querySelector('.agenda-timezone');
    if (tzEl) tzEl.textContent = `Fuso horário: ${tz}`;

    // Tenta obter CSRF token de várias fontes
    let csrfToken = null;
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfMeta) {
        csrfToken = csrfMeta.content;
    } else {
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        if (csrfInput) csrfToken = csrfInput.value;
    }

    const fmtHeader = new Intl.DateTimeFormat('pt-BR', { weekday: 'short', day: '2-digit', month: 'short' });
    const fmtTime = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' });

    // Converte pixels (relativo ao topo do grid) em minutos absolutos do dia
    function pxToMinutes(px) {
        return Math.round(px / (HOUR_HEIGHT / 60)) + START_HOUR * 60;
    }

    // Converte minutos absolutos do dia em pixels (relativo ao topo do grid)
    function minutesToPx(totalMin) {
        return Math.max(0, (totalMin - START_HOUR * 60) * (HOUR_HEIGHT / 60));
    }

    // Formata minutos absolutos como "HH:MM"
    function fmtMinutes(totalMin) {
        const h = Math.floor(totalMin / 60);
        const m = totalMin % 60;
        return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
    }

    const weekEl = document.querySelector('.agenda-week');
    if (weekEl) {
      const headerEls = document.querySelectorAll('.agenda-week-header .dow');
      headerEls.forEach(el => {
        const iso = el.getAttribute('data-iso');
        const d = new Date(iso + 'T00:00:00');
        el.textContent = fmtHeader.format(d);
        const today = new Date();
        const isToday = d.getFullYear()===today.getFullYear() && d.getMonth()===today.getMonth() && d.getDate()===today.getDate();
        if (isToday) el.classList.add('today');
      });

      const dayCols = Array.from(document.querySelectorAll('.agenda-grid .day-col'));
      const byDate = {};
      dayCols.forEach(col => {
        const iso = col.getAttribute('data-iso');
        byDate[iso] = col;
        // Marca coluna de hoje
        const d = new Date(iso + 'T00:00:00');
        const today = new Date();
        const isToday = d.getFullYear()===today.getFullYear() && d.getMonth()===today.getMonth() && d.getDate()===today.getDate();
        if (isToday) col.classList.add('today');
      });

      events.forEach(ev => {
        const startIso = (ev.start && (ev.start.dateTime || ev.start.date)) || null;
        const endIso = (ev.end && (ev.end.dateTime || ev.end.date)) || null;
        if (!startIso) return;
        const dateKey = startIso.slice(0,10);
        const col = byDate[dateKey];
        if (!col) return;
        const colorClass = 'bg-' + (ev.colorId || 'default');
        // Link do Meet, quando existente
        let meetLink = null;
        if (ev.hangoutLink) {
          meetLink = ev.hangoutLink;
        } else if (ev.conferenceData && Array.isArray(ev.conferenceData.entryPoints)) {
          const ep = ev.conferenceData.entryPoints.find(x => (x.entryPointType === 'video' || x.entryPointType === 'more') && x.uri);
          meetLink = ep && ep.uri ? ep.uri : null;
        }
        if (ev.start && ev.start.date) {
          // All-day
          const chip = document.createElement('span');
          chip.className = `badge ${colorClass}`;
          const title = ev.summary || 'Compromisso';
          const meetHtml = meetLink ? ` <a href="${meetLink}" class="meet-link ms-1" title="Abrir Meet" target="_blank" rel="noopener"><i class="bi bi-camera-video-fill"></i></a>` : '';
          chip.innerHTML = `${title}${meetHtml}`;
          col.querySelector('.allday-strip').appendChild(chip);
        } else {
          const start = new Date(startIso);
          const end = endIso ? new Date(endIso) : new Date(start.getTime() + 30*60000);
          const minutesFromMidnight = start.getHours()*60 + start.getMinutes();
          const durationMin = Math.max(20, (end - start) / 60000);
          const card = document.createElement('div');
          card.className = 'event-card bg-7';
          card.style.top = minutesToPx(minutesFromMidnight) + 'px';
          card.style.height = Math.max(20, durationMin * (HOUR_HEIGHT / 60)) + 'px';
          const meetHtml = meetLink ? ` <a href="${meetLink}" class="meet-link ms-1" title="Abrir Meet" target="_blank" rel="noopener"><i class="bi bi-camera-video-fill"></i></a>` : '';
          card.innerHTML = `<span class="event-time">${fmtTime.format(start)}</span><span class="event-title">${ev.summary || 'Compromisso'}</span>${meetHtml}` + (ev.location ? `<div class="event-loc"><i class="bi bi-geo-alt"></i> ${ev.location}</div>` : '');
          if (ev.id) card.dataset.eventId = ev.id;
          card.dataset.summary = ev.summary || 'Compromisso';
          card.dataset.description = ev.description || '';
          card.dataset.colorId = ev.colorId || '';
          card.dataset.location = ev.location || '';
          card.dataset.date = dateKey;
          card.dataset.startTime = `${String(start.getHours()).padStart(2,'0')}:${String(start.getMinutes()).padStart(2,'0')}`;
          card.dataset.endTime = endIso ? `${String(end.getHours()).padStart(2,'0')}:${String(end.getMinutes()).padStart(2,'0')}` : '';
          if (meetLink) card.dataset.hangoutLink = meetLink;
          card.style.cursor = 'pointer';
          const resize = document.createElement('div'); resize.className = 'resize-handle'; card.appendChild(resize);
          col.querySelector('.events-area').appendChild(card);
        }
      });

      // Evita que cliques no link do Meet disparem ações do card
      document.querySelectorAll('.event-card a.meet-link, .allday-strip a.meet-link').forEach(a => {
        a.addEventListener('click', (e) => { e.stopPropagation(); });
      });

      // Navegação
      function navigate(deltaDays){
        const curr = new Date(weekEl.getAttribute('data-week-start')+'T00:00:00');
        curr.setDate(curr.getDate()+deltaDays);
        const newStart = curr.toISOString().slice(0,10);
        const url = new URL(window.location.href);
        url.searchParams.set('view','semana');
        url.searchParams.set('start', newStart);
        window.location.href = url.toString();
      }
      const prevBtn = document.getElementById('prevWeek');
      const nextBtn = document.getElementById('nextWeek');
      const todayBtn = document.getElementById('goToday');
      if (prevBtn) prevBtn.addEventListener('click', () => navigate(-7));
      if (nextBtn) nextBtn.addEventListener('click', () => navigate(7));
      if (todayBtn) todayBtn.addEventListener('click', () => {
        const today = new Date();
        const iso = today.toISOString().slice(0,10);
        const url = new URL(window.location.href);
        url.searchParams.set('view','semana');
        url.searchParams.set('start', iso);
        window.location.href = url.toString();
      });

      // --- Modal de criação/edição ---
      const eventModalEl = document.getElementById('eventModal');
      const bsEventModal = eventModalEl ? bootstrap.Modal.getOrCreateInstance(eventModalEl) : null;
      const openCreateBtn = document.getElementById('openCreateEvent');
      const titleEl = document.getElementById('eventModalTitle');
      const fSummary = document.getElementById('evSummary');
      const fDescription = document.getElementById('evDescription');
      const fDate = document.getElementById('evDate');
      const fAllDay = document.getElementById('evAllDay');
      const fStart = document.getElementById('evStart');
      const fEnd = document.getElementById('evEnd');
      const fLocation = document.getElementById('evLocation');
      const fMeet = document.getElementById('evMeet');
      const fRepeat = document.getElementById('evRepeat');
      const fReminder = document.getElementById('evReminder');
      const fCalendar = document.getElementById('evCalendar');
      const topCalendarSelector = document.getElementById('calendarSelector');
      const searchInput = document.getElementById('agendaSearch');
      const timeRow = document.getElementById('timeRow');
      const saveBtn = document.getElementById('saveEventBtn');
      const deleteBtn = document.getElementById('deleteEventBtn');
      const errBox = document.getElementById('evError');
      const successBox = document.getElementById('evSuccess');
      let editingEventId = null;
      let currentCalendarId = config.currentCalendarId || 'primary';

      // Carrega calendários
      if (config.urls && config.urls.listCalendars) {
          fetch(config.urls.listCalendars)
            .then(r=>r.json())
            .then(data=>{
              if (!data.ok) return;
              const opts = data.calendars || [];
              const fill = (sel) => {
                if (!sel) return;
                sel.innerHTML = '';
                opts.forEach(c=>{
                  const o = document.createElement('option');
                  o.value = c.id; o.textContent = c.summary + (c.primary? ' (principal)' : '');
                  if (c.id === currentCalendarId) o.selected = true;
                  sel.appendChild(o);
                });
              };
              fill(topCalendarSelector);
              fill(fCalendar);
            })
            .catch(()=>{});
      }

      if (topCalendarSelector) topCalendarSelector.addEventListener('change', ()=>{
        const url = new URL(window.location.href);
        url.searchParams.set('cal', topCalendarSelector.value);
        window.location.href = url.toString();
      });
      if (searchInput) searchInput.addEventListener('keydown', (e)=>{
        if (e.key === 'Enter'){
          const url = new URL(window.location.href);
          url.searchParams.set('q', searchInput.value);
          window.location.href = url.toString();
        }
      });

      const openCreate = () => {
        editingEventId = null;
        titleEl.textContent = 'Novo Evento';
        deleteBtn.classList.add('d-none');
        errBox.classList.add('d-none');
        if (successBox) successBox.classList.add('d-none');
        fSummary.value = '';
        fDescription.value = '';
        const todayIso = new Date().toISOString().slice(0,10);
        fDate.value = todayIso;
        fAllDay.checked = false;
        timeRow.classList.remove('d-none');
        fStart.value = '08:00';
        fEnd.value = '09:00';
        fLocation.value = '';
        if (fMeet) fMeet.checked = false;
        if (fCalendar && topCalendarSelector){ fCalendar.value = topCalendarSelector.value || currentCalendarId; }
        fRepeat.value = 'none';
        fReminder.value = '';
        if (bsEventModal) bsEventModal.show();
      };
      if (openCreateBtn) openCreateBtn.addEventListener('click', openCreate);

      fAllDay.addEventListener('change', () => {
        if (fAllDay.checked) timeRow.classList.add('d-none'); else timeRow.classList.remove('d-none');
      });

      // --- Drag to move ---
      let dragStartY = null; let startTop = null; let dragging = false; let currentDayCol = null; let draggedCard = null;

      document.addEventListener('mousedown', (e) => {
          const card = e.target.closest('.event-card');
          if (card && !e.target.classList.contains('resize-handle') && !e.target.closest('a')) {
              draggedCard = card;
              dragging = true; card.classList.add('dragging');
              dragStartY = e.clientY; startTop = parseInt(card.style.top||'0',10);
              currentDayCol = card.closest('.day-col');
              e.preventDefault();
          }
      });

      document.addEventListener('mousemove', (e)=>{
        if (!dragging || !draggedCard) return;
        const card = draggedCard;
        const delta = e.clientY - dragStartY;
        const newTop = Math.max(0, startTop + delta);
        card.style.top = newTop + 'px';
        card.style.pointerEvents = 'none';
        const el = document.elementFromPoint(e.clientX, e.clientY);
        card.style.pointerEvents = '';
        const overCol = el ? el.closest('.day-col') : null;
        if (overCol && overCol !== currentDayCol){
          const area = overCol.querySelector('.events-area');
          if (area){
            area.appendChild(card);
            const newDate = overCol.getAttribute('data-iso');
            if (newDate) card.dataset.date = newDate;
            currentDayCol = overCol;
          }
        }
      });

      document.addEventListener('mouseup', async ()=>{
        if (!dragging || !draggedCard) return;
        const card = draggedCard;
        dragging = false; card.classList.remove('dragging');
        draggedCard = null;
        const topPx = parseInt(card.style.top||'0', 10);
        const startMin = pxToMinutes(topPx);
        const heightPx = parseInt(card.style.height||'0', 10);
        const durationMin = Math.round(heightPx / (HOUR_HEIGHT / 60));
        const endMin = startMin + durationMin;
        const body = { date: card.dataset.date, startTime: fmtMinutes(startMin), endTime: fmtMinutes(endMin), timeZone: tz, calendarId: topCalendarSelector?.value || currentCalendarId };
        if (card.dataset.eventId){
          try{
            const url = config.urls.updateEvent.replace('__ID__', card.dataset.eventId);
            const headers = { 'Content-Type':'application/json' };
            if (csrfToken) headers['X-CSRFToken'] = csrfToken;
            const resp = await fetch(url, { method:'PUT', headers, body: JSON.stringify(body) });
            const data = await resp.json(); if (!resp.ok || !data.ok) throw new Error(data.error || `Erro ${resp.status}`);
          } catch(e){ console.error('Falha ao mover evento:', e); }
        }
      });

      // --- Resize handle ---
      let resizing = false; let resizeStartY = 0; let startHeight = 0; let resizedCard = null;

      document.addEventListener('mousedown', (e) => {
          if (e.target.classList.contains('resize-handle')) {
              const card = e.target.closest('.event-card');
              if (card) {
                  resizedCard = card;
                  resizing=true; resizeStartY=e.clientY; startHeight=parseInt(card.style.height||'0',10);
                  e.stopPropagation(); e.preventDefault();
              }
          }
      });

      document.addEventListener('mousemove', (e)=>{
          if (!resizing || !resizedCard) return;
          const card = resizedCard;
          const delta=e.clientY - resizeStartY; const nh=Math.max(20, startHeight+delta); card.style.height = nh+'px';
      });

      document.addEventListener('mouseup', async ()=>{
          if (!resizing || !resizedCard) return;
          const card = resizedCard;
          resizing=false;
          resizedCard = null;
          const topPx = parseInt(card.style.top||'0', 10);
          const startMin = pxToMinutes(topPx);
          const heightPx = parseInt(card.style.height||'0', 10);
          const durationMin = Math.round(heightPx / (HOUR_HEIGHT / 60));
          const endMin = startMin + durationMin;
          const body = { date: card.dataset.date, startTime: fmtMinutes(startMin), endTime: fmtMinutes(endMin), timeZone: tz, calendarId: topCalendarSelector?.value || currentCalendarId };
          if (card.dataset.eventId){
            try{
              const url = config.urls.updateEvent.replace('__ID__', card.dataset.eventId);
              const headers = { 'Content-Type':'application/json' };
              if (csrfToken) headers['X-CSRFToken'] = csrfToken;
              const resp = await fetch(url, { method:'PUT', headers, body: JSON.stringify(body) });
              const data = await resp.json(); if (!resp.ok || !data.ok) throw new Error(data.error || `Erro ${resp.status}`);
            } catch(e){ console.error('Falha ao redimensionar evento:', e); }
          }
      });

      // --- Drag to create ---
      document.querySelectorAll('.events-area').forEach(area=>{
        let creating=false; let startY=0; let selDiv=null;
        area.addEventListener('mousedown', (e)=>{
            if (e.target !== area) return;
            creating=true; startY=e.offsetY; selDiv=document.createElement('div'); selDiv.style.position='absolute'; selDiv.style.left='4px'; selDiv.style.right='4px'; selDiv.style.top=startY+'px'; selDiv.style.height='20px'; selDiv.style.background='rgba(14,165,233,0.35)'; selDiv.style.borderRadius='6px'; area.appendChild(selDiv); e.preventDefault();
        });
        area.addEventListener('mousemove', (e)=>{ if (!creating || !selDiv) return; const h=Math.max(20, e.offsetY - startY); selDiv.style.height=h+'px'; });
        area.addEventListener('mouseup', (e)=>{
            if (!creating) return; creating=false;
            const dateKey=area.parentElement.dataset.iso;
            const topPx=parseInt(selDiv.style.top,10);
            const heightPx=parseInt(selDiv.style.height,10);
            area.removeChild(selDiv); selDiv=null;
            const startMin = pxToMinutes(topPx);
            const endMin = startMin + Math.round(heightPx / (HOUR_HEIGHT / 60));
            openCreate(); fDate.value = dateKey; fStart.value=fmtMinutes(startMin); fEnd.value=fmtMinutes(endMin);
        });
      });

      // Salvar (create ou update)
      saveBtn.addEventListener('click', async () => {
        const body = {
          summary: fSummary.value || 'Compromisso',
          description: fDescription.value || undefined,
          date: fDate.value,
          allDay: fAllDay.checked,
          startTime: fAllDay.checked ? null : fStart.value,
          endTime: fAllDay.checked ? null : fEnd.value,
          timeZone: tz,
          location: fLocation.value || undefined,
          conference: !!(fMeet && fMeet.checked),
          calendarId: fCalendar?.value || currentCalendarId,
          recurrence: (function(){
            if (fRepeat.value==='none') return undefined;
            const map = { daily:'DAILY', weekly:'WEEKLY', monthly:'MONTHLY' };
            return [`RRULE:FREQ=${map[fRepeat.value]};COUNT=5`];
          })(),
          reminders: (function(){
            let m = parseInt(fReminder.value||'0',10);
            if (!m) m = 10;
            return { useDefault: false, overrides: [{ method:'popup', minutes:m }] };
          })()
        };
        errBox.classList.add('d-none');
        try {
          let resp;
          if (editingEventId) {
            const url = config.urls.updateEvent.replace('__ID__', editingEventId);
            const headers = { 'Content-Type': 'application/json' };
            if (csrfToken) headers['X-CSRFToken'] = csrfToken;
            resp = await fetch(url, { method: 'PUT', headers, body: JSON.stringify(body) });
          } else {
            const headers = { 'Content-Type': 'application/json' };
            if (csrfToken) headers['X-CSRFToken'] = csrfToken;
            resp = await fetch(config.urls.createEvent, { method: 'POST', headers, body: JSON.stringify(body) });
          }
          const data = await resp.json();
          if (!resp.ok || !data.ok) throw new Error(data.error || `Erro ${resp.status}`);
          let meetLink = null;
          const ev = data.event || {};
          if (ev.hangoutLink) {
            meetLink = ev.hangoutLink;
          } else if (ev.conferenceData && Array.isArray(ev.conferenceData.entryPoints)) {
            const videoEp = ev.conferenceData.entryPoints.find(ep => (ep.entryPointType === 'video' || ep.entryPointType === 'more') && ep.uri);
            meetLink = videoEp && videoEp.uri ? videoEp.uri : null;
          }
          if (meetLink && successBox) {
            successBox.innerHTML = `Evento criado. Link da reunião: <a href="${meetLink}" target="_blank" rel="noopener">${meetLink}</a>`;
            successBox.classList.remove('d-none');
          } else {
            if (bsEventModal) bsEventModal.hide();
            window.location.reload();
          }
        } catch (e) {
          errBox.textContent = e.message || String(e);
          errBox.classList.remove('d-none');
        }
      });

      // Excluir
      deleteBtn.addEventListener('click', async () => {
        if (!editingEventId) return;
        errBox.classList.add('d-none');
        try {
          const delUrl = config.urls.deleteEvent.replace('__ID__', editingEventId) + `?calendarId=${encodeURIComponent(fCalendar?.value || currentCalendarId)}`;
          const headers = {};
          if (csrfToken) headers['X-CSRFToken'] = csrfToken;
          const resp = await fetch(delUrl, { method: 'DELETE', headers });
          const data = await resp.json();
          if (!resp.ok || !data.ok) throw new Error(data.error || `Erro ${resp.status}`);
          if (bsEventModal) bsEventModal.hide();
          window.location.reload();
        } catch (e) {
          errBox.textContent = e.message || String(e);
          errBox.classList.remove('d-none');
        }
      });
    }
});
