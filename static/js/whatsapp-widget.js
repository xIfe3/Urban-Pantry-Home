// WhatsApp Widget and Order Functionality
(function () {
  // WhatsApp Business Number (replace with actual number)
  const WHATSAPP_PHONE = "2347034396303"; // Urban Pantry WhatsApp number
  const WHATSAPP_URL = `https://wa.me/${WHATSAPP_PHONE}`;

  // Create floating WhatsApp button
  function createWhatsAppWidget() {
    const widget = document.createElement("div");
    widget.id = "whatsapp-widget";
    widget.innerHTML = `
      <a href="${WHATSAPP_URL}?text=Hi%20Urban%20Pantry!%20I%20need%20help%20with%20an%20order"
         target="_blank"
         rel="noopener noreferrer"
         title="Chat with us on WhatsApp"
         class="whatsapp-button">
        <i class="fab fa-whatsapp"></i>
        <span class="whatsapp-tooltip">Chat with us</span>
      </a>
    `;

    // Inject CSS
    const style = document.createElement("style");
    style.textContent = `
      #whatsapp-widget {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 1000;
        animation: slideInUp 0.5s ease-out;
      }

      .whatsapp-button {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 60px;
        height: 60px;
        background: linear-gradient(135deg, #25d366 0%, #20ba5a 100%);
        border-radius: 50%;
        color: white;
        font-size: 28px;
        text-decoration: none;
        box-shadow: 0 4px 12px rgba(37, 211, 102, 0.4);
        transition: all 0.3s ease;
        position: relative;
      }

      .whatsapp-button:hover {
        transform: scale(1.1);
        box-shadow: 0 6px 20px rgba(37, 211, 102, 0.6);
      }

      .whatsapp-button:active {
        transform: scale(0.95);
      }

      .whatsapp-tooltip {
        position: absolute;
        right: 75px;
        background: #25d366;
        color: white;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
        white-space: nowrap;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.3s ease;
        font-family: 'DM Sans', sans-serif;
      }

      .whatsapp-button:hover .whatsapp-tooltip {
        opacity: 1;
      }

      @keyframes slideInUp {
        from {
          transform: translateY(100px);
          opacity: 0;
        }
        to {
          transform: translateY(0);
          opacity: 1;
        }
      }

      @media (max-width: 768px) {
        #whatsapp-widget {
          bottom: 20px;
          right: 20px;
        }

        .whatsapp-button {
          width: 55px;
          height: 55px;
          font-size: 24px;
        }

        .whatsapp-tooltip {
          font-size: 11px;
          right: 70px;
        }
      }
    `;

    document.head.appendChild(style);
    document.body.appendChild(widget);
  }

  // Generate WhatsApp message for order
  window.sendOrderViaWhatsApp = function (orderDetails) {
    const message = encodeURIComponent(
      `📦 *New Order Request*\n\n` +
        `Customer Name: ${orderDetails.customer_name}\n` +
        `Email: ${orderDetails.email}\n` +
        `Phone: ${orderDetails.phone || "Not provided"}\n` +
        `Address: ${orderDetails.address}\n\n` +
        `*Order Items:*\n${orderDetails.items}\n\n` +
        `*Total: N${orderDetails.total}*\n` +
        `Payment Method: ${orderDetails.payment_method}`,
    );

    const whatsappUrl = `https://wa.me/${WHATSAPP_PHONE}?text=${message}`;
    window.open(whatsappUrl, "_blank");
  };

  // Initialize when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", createWhatsAppWidget);
  } else {
    createWhatsAppWidget();
  }
})();
