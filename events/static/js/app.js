const TicketHub = (() => {
  async function postJSON(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  }

  function initSeatMap() {
    const map = document.querySelector(".seat-map");
    if (!map) return;

    const eventId = map.dataset.eventId;
    const emailInput = document.getElementById("buyer-email");
    const messageBox = document.getElementById("hold-message");

    function showMessage(text, kind) {
      messageBox.textContent = text;
      messageBox.className = `message message-${kind}`;
      messageBox.hidden = false;
    }

    map.addEventListener("click", async (event) => {
      const seatButton = event.target.closest(".seat");
      if (!seatButton || seatButton.disabled) return;

      const email = emailInput.value.trim();
      if (!email) {
        showMessage("Сначала укажи email.", "error");
        emailInput.focus();
        return;
      }

      seatButton.disabled = true;
      const seatId = seatButton.dataset.seatId;
      const { ok, status, data } = await postJSON(
        `/api/events/${eventId}/seats/${seatId}/hold`,
        { buyer_email: email }
      );

      if (ok) {
        window.location.href = `/orders/${data.order_id}/`;
        return;
      }

      seatButton.disabled = false;
      if (status === 409) {
        seatButton.classList.add("seat-taken");
        seatButton.disabled = true;
        showMessage(data.detail || "Место уже занято.", "error");
      } else {
        showMessage("Не получилось забронировать, попробуй ещё раз.", "error");
      }
    });
  }

  function initOrderPage() {
    const box = document.getElementById("order-status");
    if (!box) return;

    const orderId = box.dataset.orderId;
    const payButton = document.getElementById("pay-button");
    const payBlock = document.getElementById("pay-block");
    const processingBlock = document.getElementById("processing-block");
    const ticketBlock = document.getElementById("ticket-block");
    const ticketLink = document.getElementById("ticket-link");
    const statusBadge = document.getElementById("status-badge");

    const STATUS_LABELS = {
      HOLD: "Забронировано",
      PAID: "Оплачено",
      CANCELLED: "Отменено",
      EXPIRED: "Истекло",
    };

    function renderStatus(status) {
      statusBadge.textContent = STATUS_LABELS[status] || status;
      statusBadge.className = `status-badge status-${status.toLowerCase()}`;
    }

    async function poll(orderIdInner) {
      for (let attempt = 0; attempt < 20; attempt++) {
        await new Promise((r) => setTimeout(r, 1000));
        const res = await fetch(`/api/orders/${orderIdInner}`);
        const data = await res.json();
        if (data.status !== "HOLD") {
          renderStatus(data.status);
          processingBlock.hidden = true;
          if (data.status === "PAID" && data.ticket_pdf_url) {
            ticketLink.href = data.ticket_pdf_url;
            ticketBlock.hidden = false;
          }
          return;
        }
      }
      processingBlock.hidden = true;
      payBlock.hidden = false;
    }

    if (payButton) {
      payButton.addEventListener("click", async () => {
        payBlock.hidden = true;
        processingBlock.hidden = false;
        const { ok } = await postJSON(`/api/orders/${orderId}/pay`);
        if (!ok) {
          processingBlock.hidden = true;
          payBlock.hidden = false;
          return;
        }
        poll(orderId);
      });
    }
  }

  return { initSeatMap, initOrderPage };
})();
