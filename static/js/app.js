const socket = io();
let cartState = window.initialCart || { items: [], total: 0, count: 0 };

function formatCurrency(value) {
    return `$${Number(value).toFixed(2)}`;
}

function showToast(message) {
    let toast = document.querySelector(".toast");

    if (!toast) {
        toast = document.createElement("div");
        toast.className = "toast";
        document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.classList.add("show");

    window.clearTimeout(showToast.timeoutId);
    showToast.timeoutId = window.setTimeout(() => {
        toast.classList.remove("show");
    }, 1800);
}

function updateHeaderCount() {
    const countNode = document.querySelector("#cart-count");
    if (countNode) {
        countNode.textContent = cartState.count;
    }
}

function renderCartPage() {
    if (!window.isCartPage) {
        return;
    }

    const itemsContainer = document.querySelector("#cart-items");
    const summaryCount = document.querySelector("#summary-count");
    const summaryTotal = document.querySelector("#summary-total");

    if (!itemsContainer) {
        return;
    }

    summaryCount.textContent = cartState.count;
    summaryTotal.textContent = formatCurrency(cartState.total);

    if (!cartState.items.length) {
        itemsContainer.innerHTML = `
            <div class="empty-state">
                <h3>Your cart is empty</h3>
                <p>Add a few products from the shop to see them here.</p>
            </div>
        `;
        return;
    }

    itemsContainer.innerHTML = cartState.items
        .map(
            (item) => `
                <article class="cart-item">
                    <img src="${item.image}" alt="${item.name}">
                    <div>
                        <h3>${item.name}</h3>
                        <div class="cart-meta">Price: ${formatCurrency(item.price)}</div>
                        <div class="cart-meta">Subtotal: ${formatCurrency(item.subtotal)}</div>
                        <div class="qty-controls">
                            <button class="qty-btn" data-product-id="${item.id}" data-action="decrease">-</button>
                            <strong>${item.quantity}</strong>
                            <button class="qty-btn" data-product-id="${item.id}" data-action="increase">+</button>
                        </div>
                    </div>
                    <strong>${formatCurrency(item.subtotal)}</strong>
                </article>
            `
        )
        .join("");
}

async function postJson(url, payload) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        throw new Error("Request failed.");
    }

    return response.json();
}

async function addToCart(productId) {
    cartState = await postJson("/api/cart/add", { product_id: productId });
    updateHeaderCount();
    renderCartPage();
    showToast("Added to cart");
}

async function updateCartQuantity(productId, nextQuantity) {
    cartState = await postJson("/api/cart/update", {
        product_id: productId,
        quantity: nextQuantity,
    });
    updateHeaderCount();
    renderCartPage();
}

document.addEventListener("click", async (event) => {
    const addButton = event.target.closest(".add-to-cart-btn");
    if (addButton) {
        const productId = Number(addButton.dataset.productId);
        addButton.disabled = true;

        try {
            await addToCart(productId);
        } catch (error) {
            showToast("Could not add product");
        } finally {
            addButton.disabled = false;
        }
    }

    const qtyButton = event.target.closest(".qty-btn");
    if (qtyButton) {
        const productId = Number(qtyButton.dataset.productId);
        const item = cartState.items.find((entry) => entry.id === productId);
        if (!item) {
            return;
        }

        const nextQuantity =
            qtyButton.dataset.action === "increase"
                ? item.quantity + 1
                : item.quantity - 1;

        try {
            await updateCartQuantity(productId, nextQuantity);
        } catch (error) {
            showToast("Could not update cart");
        }
    }
});

socket.on("cart_updated", (data) => {
    cartState = data;
    updateHeaderCount();
    renderCartPage();
});

updateHeaderCount();
renderCartPage();
