// Use relative paths for Vercel deployment
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
    }, 2000);
}

function updateHeaderCount() {
    const countNode = document.querySelector("#cart-count");
    if (countNode) {
        countNode.textContent = cartState.count;
    }
}

function renderCartPage() {
    if (!window.isCartPage) return;
    const itemsContainer = document.querySelector("#cart-items");
    const summaryCount = document.querySelector("#summary-count");
    const summaryTotal = document.querySelector("#summary-total");
    if (!itemsContainer) return;
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
    
    itemsContainer.innerHTML = cartState.items.map(item => `
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
    `).join("");
}

function renderCheckoutPage() {
    if (!window.isCheckoutPage) return;
    const itemsContainer = document.querySelector("#checkout-items");
    const countNode = document.querySelector("#checkout-count");
    const totalNode = document.querySelector("#checkout-total");
    if (!itemsContainer) return;
    countNode.textContent = cartState.count;
    totalNode.textContent = formatCurrency(cartState.total);
    
    if (!cartState.items.length) {
        itemsContainer.innerHTML = `<p style="color: #6b7280;">Your cart is empty.</p>`;
        return;
    }
    
    itemsContainer.innerHTML = cartState.items.map(item => `
        <div class="checkout-item">
            <span>${item.name} × ${item.quantity}</span>
            <strong>${formatCurrency(item.subtotal)}</strong>
        </div>
    `).join("");
}

async function postJson(url, payload) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    
    if (!response.ok) throw new Error("Request failed.");
    return response.json();
}

async function addToCart(productId) {
    cartState = await postJson("/api/cart/add", { product_id: productId });
    updateHeaderCount();
    renderCartPage();
    renderCheckoutPage();
    showToast("Added to cart");
}

async function updateCartQuantity(productId, nextQuantity) {
    cartState = await postJson("/api/cart/update", {
        product_id: productId,
        quantity: nextQuantity,
    });
    updateHeaderCount();
    renderCartPage();
    renderCheckoutPage();
}

async function clearCart() {
    cartState = await postJson("/api/cart/clear", {});
    updateHeaderCount();
    renderCartPage();
    showToast("Cart cleared");
}

async function getAiRecommendations(query) {
    const resultsContainer = document.querySelector("#ai-results");
    if (!resultsContainer) return;
    
    resultsContainer.innerHTML = `<p style="opacity: 0.8;">Getting recommendations...</p>`;
    
    try {
        const data = await postJson("/api/ai/recommend", { query: query });
        resultsContainer.innerHTML = `
            <p class="ai-message">${data.message}</p>
            <div class="ai-products">
                ${data.recommendations.map(product => `
                    <div class="product-card">
                        <img src="${product.image}" alt="${product.name}">
                        <div class="product-content">
                            <span class="product-category">${product.category}</span>
                            <h3>${product.name}</h3>
                            <p class="price">${formatCurrency(product.price)}</p>
                            <button class="primary-btn add-to-cart-btn" data-product-id="${product.id}">Add to cart</button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        resultsContainer.innerHTML = `<p style="opacity: 0.8;">Could not get recommendations. Please try again.</p>`;
    }
}

async function placeOrder() {
    if (!cartState.items.length) {
        showToast("Your cart is empty!");
        return;
    }
    
    try {
        const data = await postJson("/api/checkout", {});
        const modal = document.querySelector("#order-success-modal");
        const messageNode = document.querySelector("#order-message");
        
        if (modal && messageNode) {
            messageNode.textContent = `${data.message} Order ID: ${data.order_id}`;
            modal.style.display = "flex";
        }
        
        cartState = { items: [], total: 0, count: 0 };
        updateHeaderCount();
        renderCheckoutPage();
    } catch (error) {
        showToast("Could not place order. Please try again.");
    }
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
        if (!item) return;
        
        const nextQuantity = qtyButton.dataset.action === "increase" ? item.quantity + 1 : item.quantity - 1;
        
        try {
            await updateCartQuantity(productId, nextQuantity);
        } catch (error) {
            showToast("Could not update cart");
        }
    }
    
    const clearCartBtn = event.target.closest("#clear-cart-btn");
    if (clearCartBtn) {
        try {
            await clearCart();
        } catch (error) {
            showToast("Could not clear cart");
        }
    }
    
    const aiSubmitBtn = event.target.closest("#ai-submit");
    if (aiSubmitBtn) {
        const queryInput = document.querySelector("#ai-query");
        if (queryInput) await getAiRecommendations(queryInput.value);
    }
});

document.addEventListener("keypress", async (event) => {
    if (event.key === "Enter") {
        const aiInput = event.target.closest("#ai-query");
        if (aiInput) await getAiRecommendations(aiInput.value);
    }
});

document.addEventListener("submit", async (event) => {
    if (event.target.closest("#checkout-form")) {
        event.preventDefault();
        await placeOrder();
    }
});

updateHeaderCount();
renderCartPage();
renderCheckoutPage();

