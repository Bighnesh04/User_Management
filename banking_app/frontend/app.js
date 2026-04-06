const $ = (id) => document.getElementById(id);

const state = {
  apiBase: localStorage.getItem("apiBase") || "http://127.0.0.1:8000",
  token: localStorage.getItem("token") || "",
};

const output = $("output");

function setOutput(label, data) {
  output.textContent = `${label}\n\n${typeof data === "string" ? data : JSON.stringify(data, null, 2)}`;
}

function updateSessionUI() {
  $("apiBase").value = state.apiBase;
  $("tokenView").value = state.token;
  $("sessionInfo").textContent = state.token ? "Logged in" : "Not logged in";
}

async function api(path, { method = "GET", body, auth = true, form = false } = {}) {
  const headers = {};
  if (!form) headers["Content-Type"] = "application/json";
  if (auth && state.token) headers.Authorization = `Bearer ${state.token}`;

  const response = await fetch(`${state.apiBase}${path}`, {
    method,
    headers,
    body: body
      ? form
        ? new URLSearchParams(body)
        : JSON.stringify(body)
      : undefined,
  });

  let data;
  const text = await response.text();
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = text;
  }

  if (!response.ok) {
    throw new Error(typeof data === "string" ? data : JSON.stringify(data));
  }

  return data;
}

function toNumber(value) {
  return value ? Number(value) : undefined;
}

$("saveApiBaseBtn").addEventListener("click", () => {
  state.apiBase = $("apiBase").value.trim() || "http://127.0.0.1:8000";
  localStorage.setItem("apiBase", state.apiBase);
  setOutput("API Base Updated", { apiBase: state.apiBase });
});

$("logoutBtn").addEventListener("click", () => {
  state.token = "";
  localStorage.removeItem("token");
  updateSessionUI();
  setOutput("Session", "Logged out successfully.");
});

$("registerBtn").addEventListener("click", async () => {
  try {
    const data = await api("/auth/register", {
      method: "POST",
      auth: false,
      body: {
        full_name: $("regName").value,
        email: $("regEmail").value,
        password: $("regPassword").value,
      },
    });
    setOutput("Register Success", data);
  } catch (err) {
    setOutput("Register Error", String(err));
  }
});

$("loginBtn").addEventListener("click", async () => {
  try {
    const data = await api("/auth/login", {
      method: "POST",
      auth: false,
      form: true,
      body: {
        username: $("loginEmail").value,
        password: $("loginPassword").value,
      },
    });
    state.token = data.access_token;
    localStorage.setItem("token", state.token);
    updateSessionUI();
    setOutput("Login Success", data);
  } catch (err) {
    setOutput("Login Error", String(err));
  }
});

$("kycBtn").addEventListener("click", async () => {
  try {
    const data = await api("/auth/kyc/verify", {
      method: "POST",
      body: { pan_number: $("pan").value, aadhaar_number: $("aadhaar").value },
    });
    setOutput("KYC Verified", data);
  } catch (err) {
    setOutput("KYC Error", String(err));
  }
});

$("createAccountBtn").addEventListener("click", async () => {
  try {
    const data = await api("/accounts", {
      method: "POST",
      body: {
        account_type: $("accountType").value,
        initial_deposit: Number($("initialDeposit").value || 0),
      },
    });
    setOutput("Account Created", data);
  } catch (err) {
    setOutput("Create Account Error", String(err));
  }
});

$("listAccountsBtn").addEventListener("click", async () => {
  try {
    const data = await api("/accounts");
    setOutput("My Accounts", data);
  } catch (err) {
    setOutput("Accounts Error", String(err));
  }
});

$("depositBtn").addEventListener("click", async () => {
  try {
    const data = await api("/transactions/deposit", {
      method: "POST",
      body: {
        destination_account_id: toNumber($("depDest").value),
        amount: Number($("depAmount").value || 0),
        location: $("depLocation").value || null,
      },
    });
    setOutput("Deposit Success", data);
  } catch (err) {
    setOutput("Deposit Error", String(err));
  }
});

$("withdrawBtn").addEventListener("click", async () => {
  try {
    const data = await api("/transactions/withdraw", {
      method: "POST",
      body: {
        source_account_id: toNumber($("wdSource").value),
        amount: Number($("wdAmount").value || 0),
        location: $("wdLocation").value || null,
      },
    });
    setOutput("Withdraw Success", data);
  } catch (err) {
    setOutput("Withdraw Error", String(err));
  }
});

$("transferBtn").addEventListener("click", async () => {
  try {
    const data = await api("/transactions/transfer", {
      method: "POST",
      body: {
        source_account_id: toNumber($("trSource").value),
        destination_account_id: toNumber($("trDest").value),
        amount: Number($("trAmount").value || 0),
        location: $("trLocation").value || null,
      },
    });
    setOutput("Transfer Success", data);
  } catch (err) {
    setOutput("Transfer Error", String(err));
  }
});

$("emiBtn").addEventListener("click", async () => {
  try {
    const data = await api("/loans/emi", {
      method: "POST",
      auth: false,
      body: {
        principal: Number($("loanPrincipal").value || 0),
        annual_interest_rate: Number($("loanRate").value || 0),
        tenure_months: Number($("loanMonths").value || 0),
      },
    });
    setOutput("EMI", data);
  } catch (err) {
    setOutput("EMI Error", String(err));
  }
});

$("applyLoanBtn").addEventListener("click", async () => {
  try {
    const data = await api("/loans/apply", {
      method: "POST",
      body: {
        principal: Number($("loanPrincipal").value || 0),
        annual_interest_rate: Number($("loanRate").value || 0),
        tenure_months: Number($("loanMonths").value || 0),
      },
    });
    setOutput("Loan Applied", data);
  } catch (err) {
    setOutput("Loan Error", String(err));
  }
});

$("myLoansBtn").addEventListener("click", async () => {
  try {
    const data = await api("/loans/my");
    setOutput("My Loans", data);
  } catch (err) {
    setOutput("My Loans Error", String(err));
  }
});

$("adminUsersBtn").addEventListener("click", async () => {
  try {
    const data = await api("/auth/admin/users");
    setOutput("Admin Users", data);
  } catch (err) {
    setOutput("Admin Users Error", String(err));
  }
});

$("adminTxBtn").addEventListener("click", async () => {
  try {
    const data = await api("/transactions/admin/all");
    setOutput("Admin Transactions", data);
  } catch (err) {
    setOutput("Admin Transactions Error", String(err));
  }
});

$("adminFraudBtn").addEventListener("click", async () => {
  try {
    const data = await api("/transactions/admin/fraud-alerts");
    setOutput("Admin Fraud Alerts", data);
  } catch (err) {
    setOutput("Admin Fraud Alerts Error", String(err));
  }
});

$("adminPendingLoansBtn").addEventListener("click", async () => {
  try {
    const data = await api("/loans/admin/pending");
    setOutput("Admin Pending Loans", data);
  } catch (err) {
    setOutput("Admin Pending Loans Error", String(err));
  }
});

updateSessionUI();
