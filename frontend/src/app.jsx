import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Zap, 
  MessageSquare, 
  Terminal, 
  ShieldCheck, 
  CreditCard, 
  Cpu, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  Bot, 
  User, 
  Send, 
  TrendingUp, 
  Lock, 
  Sparkles,
  ChevronRight,
  ShieldAlert,
  Activity
} from 'lucide-react';

const API_BASE = "http://localhost:8000";

export default function App() {
  const [activeTab, setActiveTab] = useState("mode1"); // "mode1" = A2A Swarm, "mode2" = Chatbot + Modal
  
  // Shared State
  const [catalog, setCatalog] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [selectedAuditLog, setSelectedAuditLog] = useState(null);

  // Mode 1 State (A2A Swarm)
  const [swarmGoal, setSwarmGoal] = useState("Equip a senior full-stack developer with an ultra-sharp workspace under ₹11,000");
  const [maxBudget, setMaxBudget] = useState(11000);
  const [swarmLoading, setSwarmLoading] = useState(false);
  const [packets, setPackets] = useState([]);
  const [settlementResult, setSettlementResult] = useState(null);

  // Mode 2 State (Conversational Copilot)
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hello! I am your AI Shopping Copilot. You can browse our developer hardware catalog, compare specs, or ask for product recommendations."
    }
  ]);
  const [chatInput, setChatInput] = useState("I want to buy the Low-Profile Mechanical Keyboard");
  const [chatLoading, setChatLoading] = useState(false);
  const [pendingIntent, setPendingIntent] = useState(null);
  const sessionId = "session_dev_001";

  const fetchCatalogAndLogs = async () => {
    try {
      const [catRes, logRes] = await Promise.all([
        axios.get(`${API_BASE}/api/catalog`),
        axios.get(`${API_BASE}/api/audit-ledger`)
      ]);
      setCatalog(catRes.data);
      setAuditLogs(logRes.data);
    } catch (err) {
      console.error("Failed to fetch initial data:", err);
    }
  };

  useEffect(() => {
    fetchCatalogAndLogs();
  }, []);

  // --------------------------------------------------------------------------
  // Mode 1: Trigger Live A2A Cognitive Swarm Stream
  // --------------------------------------------------------------------------
  const handleLaunchSwarm = async (e) => {
    e.preventDefault();
    setSwarmLoading(true);
    setPackets([]);
    setSettlementResult(null);

    try {
      const response = await fetch(`${API_BASE}/api/protocol/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_goal: swarmGoal, max_budget: Number(maxBudget) })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const raw = decoder.decode(value);
        const lines = raw.split("\n\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = JSON.parse(line.replace("data: ", ""));
            setPackets((prev) => [...prev, data]);

            if (data.layer === "RAZORPAY_SETTLEMENT_RAILS") {
              setSettlementResult(data.payload);
            }
          }
        }
      }
      await fetchCatalogAndLogs();
    } catch (err) {
      console.error(err);
    } finally {
      setSwarmLoading(false);
    }
  };

  // --------------------------------------------------------------------------
  // Mode 2: Conversational Chat Turn & Intent Formulation
  // --------------------------------------------------------------------------
  const handleSendChatMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userText = chatInput;
    setChatInput("");
    setMessages((prev) => [...prev, { role: "user", content: userText }]);
    setChatLoading(true);

    try {
      const res = await axios.post(`${API_BASE}/api/chat`, {
        message: userText,
        chat_history: messages,
        session_id: sessionId
      });

      setMessages((prev) => [...prev, { role: "assistant", content: res.data.reply }]);
      if (res.data.proposed_intent) {
        setPendingIntent(res.data.proposed_intent);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setChatLoading(false);
    }
  };

  // Mode 2: Trigger Razorpay Checkout Modal
 // Helper to load Razorpay SDK dynamically
  const loadRazorpayScript = () => {
    return new Promise((resolve) => {
      if (window.Razorpay) {
        resolve(true);
        return;
      }
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.body.appendChild(script);
    });
  };

  // Mode 2: Trigger Razorpay Checkout Modal
  const handleConfirmAndPayModal = async () => {
    if (!pendingIntent) return;
    setChatLoading(true);

    try {
      const isLoaded = await loadRazorpayScript();
      if (!isLoaded) {
        alert("Failed to load Razorpay Checkout SDK. Please check your connection.");
        return;
      }

      const intentToSubmit = { ...pendingIntent, confirmed_by_user: true };
      const res = await axios.post(`${API_BASE}/api/orders/confirm-and-create`, {
        intent: intentToSubmit
      });

      const { gate_result, execution, key_id } = res.data;

      if (gate_result.approved && execution.order_id) {
        const options = {
          key: key_id,
          amount: execution.amount_paid_inr * 100, // in paise
          currency: "INR",
          name: "Aegis-AP2 Merchant Store",
          description: `Order ${execution.order_id}`,
          order_id: execution.order_id,
          handler: function (response) {
            alert(`Payment Succeeded! Razorpay Payment ID: ${response.razorpay_payment_id}`);
            fetchCatalogAndLogs();
          },
          prefill: {
            name: "Harshit Jethi",
            email: "harshitjethi8@gmail.com",
            contact: "9999999999"
          },
          theme: { color: "#2563eb" }
        };

        const rzp = new window.Razorpay(options);

        rzp.on("payment.failed", async function (response) {
          const errorObj = response.error || {};
          try {
            const failRes = await axios.post(`${API_BASE}/api/orders/handle-failure`, {
              session_id: sessionId,
              order_id: errorObj.metadata?.order_id || execution.order_id,
              error_code: errorObj.code || "BAD_REQUEST_ERROR",
              error_description: errorObj.description || "Test payment declined by bank.",
              sku: pendingIntent.sku
            });

            setMessages((prev) => [
              ...prev,
              {
                role: "assistant",
                content: `⚠️ **Payment Attempt Declined**\n\n${failRes.data.recovery_message}\n\nYour intent for **${pendingIntent.item_name}** is preserved. Click **Confirm & Pay** to retry.`
              }
            ]);
          } catch (err) {
            console.error("Failed to log decline:", err);
          }
          await fetchCatalogAndLogs();
        });

        rzp.open();
      }
      await fetchCatalogAndLogs();
    } catch (err) {
      alert(`Gate Rejection: ${err.response?.data?.detail || err.message}`);
      await fetchCatalogAndLogs();
    } finally {
      setChatLoading(false);
    }
  };
  // Chaos Injection
  const triggerChaosStock = async (sku, newStock) => {
    await axios.post(`${API_BASE}/api/chaos/set-stock`, { sku, new_stock: newStock });
    await fetchCatalogAndLogs();
  };

  return (
    <div className="min-h-screen bg-[#07090E] text-slate-100 p-6 space-y-6">
      
      {/* Top Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-blue-600/20 border border-blue-500/40 rounded-xl text-blue-400">
            <Lock className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              Aegis-AP2 Dual-Mode Command Cockpit
              <span className="text-[10px] font-mono bg-blue-500/10 border border-blue-500/30 text-blue-400 px-2 py-0.5 rounded-full">
                Track 01 Enterprise Gateway
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Autonomous A2A Cognitive Swarm + Conversational Checkout Modal on Razorpay Rails
            </p>
          </div>
        </div>

        {/* Tab Selector & Controls */}
        <div className="flex items-center space-x-3">
          <div className="bg-slate-900 border border-slate-800 p-1 rounded-xl flex">
            <button
              onClick={() => setActiveTab("mode1")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === "mode1" ? "bg-blue-600 text-white shadow" : "text-slate-400 hover:text-white"
              }`}
            >
              <Zap className="w-3.5 h-3.5" /> Mode 1: A2A Swarm
            </button>
            <button
              onClick={() => setActiveTab("mode2")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === "mode2" ? "bg-blue-600 text-white shadow" : "text-slate-400 hover:text-white"
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" /> Mode 2: Copilot & Modal
            </button>
          </div>

          <button 
            onClick={fetchCatalogAndLogs}
            className="p-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg text-slate-400 hover:text-white transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Shared Metrics Rail */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-3">
          <div className="p-2.5 bg-purple-500/10 rounded-lg text-purple-400"><Bot className="w-5 h-5" /></div>
          <div>
            <div className="text-[10px] text-slate-500 font-mono uppercase">AI Buyer Reasoning</div>
            <div className="text-xs font-semibold text-slate-200">ReAct Chain-of-Thought</div>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-3">
          <div className="p-2.5 bg-emerald-500/10 rounded-lg text-emerald-400"><TrendingUp className="w-5 h-5" /></div>
          <div>
            <div className="text-[10px] text-slate-500 font-mono uppercase">Merchant Revenue Agent</div>
            <div className="text-xs font-semibold text-emerald-400">+43.6% GMV Bundle Growth</div>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-3">
          <div className="p-2.5 bg-amber-500/10 rounded-lg text-amber-400"><ShieldAlert className="w-5 h-5" /></div>
          <div>
            <div className="text-[10px] text-slate-500 font-mono uppercase">Adversarial Sentinel</div>
            <div className="text-xs font-semibold text-slate-200">Zero Injection Verified</div>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-3">
          <div className="p-2.5 bg-blue-500/10 rounded-lg text-blue-400"><CreditCard className="w-5 h-5" /></div>
          <div>
            <div className="text-[10px] text-slate-500 font-mono uppercase">Razorpay Test Rails</div>
            <div className="text-xs font-semibold text-slate-200">HMAC-SHA256 Signed</div>
          </div>
        </div>
      </div>

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* =================================================================== */}
        {/* LEFT PANE: MODE 1 (SWARM) OR MODE 2 (COPILOT) (7 Cols)              */}
        {/* =================================================================== */}
        <div className="lg:col-span-7 space-y-6">

          {activeTab === "mode1" ? (
            /* ---------------- MODE 1: A2A SWARM ---------------- */
            <div className="space-y-6">
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-blue-400" /> Mode 1: Autonomous Procurement Swarm
                </h2>
                <form onSubmit={handleLaunchSwarm} className="space-y-3">
                  <div>
                    <label className="text-[11px] text-slate-400 font-mono">Autonomous Buyer Mandate</label>
                    <textarea
                      value={swarmGoal}
                      onChange={(e) => setSwarmGoal(e.target.value)}
                      rows={2}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-200 resize-none font-mono focus:border-blue-500 focus:outline-none mt-1"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] text-slate-400 font-mono">Hard Spending Ceiling (₹)</label>
                    <input
                      type="number"
                      value={maxBudget}
                      onChange={(e) => setMaxBudget(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200 font-mono focus:border-blue-500 focus:outline-none mt-1"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={swarmLoading}
                    className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium text-xs flex items-center justify-center gap-2 transition"
                  >
                    {swarmLoading ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Running Tri-Agent Swarm (Buyer ↔ Seller ↔ Sentinel)...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        Dispatch Autonomous Negotiation Swarm
                      </>
                    )}
                  </button>
                </form>
              </div>

              {/* Real-time Token Packet Stream */}
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-slate-300 flex items-center gap-2 font-mono">
                    <Terminal className="w-4 h-4 text-blue-400" /> Live Cognitive Reasoning Packets
                  </span>
                  <span className="text-[10px] font-mono text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">
                    SSE Active
                  </span>
                </div>

                <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-xs space-y-2.5 max-h-[320px] overflow-y-auto">
                  {packets.length === 0 ? (
                    <div className="text-slate-600 text-center py-12">
                      Ready. Launch the swarm to watch the real-time A2A negotiation.
                    </div>
                  ) : (
                    packets.map((p, idx) => (
                      <div key={idx} className={`p-3 rounded-lg border text-[11px] space-y-1 ${
                        p.layer.includes("BUYER") ? "border-purple-500/30 bg-purple-950/20" :
                        p.layer.includes("SELLER") ? "border-emerald-500/30 bg-emerald-950/20" :
                        p.layer.includes("SENTINEL") ? "border-amber-500/30 bg-amber-950/20" :
                        "border-blue-500/30 bg-blue-950/20"
                      }`}>
                        <div className="flex justify-between text-[10px]">
                          <span className="font-bold text-slate-200">{p.sender}</span>
                          <span className="text-slate-400 font-mono">{p.layer}</span>
                        </div>
                        <pre className="text-slate-300 text-[10px] overflow-x-auto whitespace-pre-wrap">
                          {JSON.stringify(p.payload, null, 2)}
                        </pre>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          ) : (
            /* ---------------- MODE 2: CONVERSATIONAL COPILOT ---------------- */
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl flex flex-col h-[600px] shadow-lg">
              <div className="p-3 border-b border-slate-800 flex justify-between items-center text-xs font-mono text-slate-400">
                <span className="flex items-center gap-1.5"><Bot className="w-4 h-4 text-blue-400" /> Interactive Shopping Thread</span>
                <span>Session: {sessionId}</span>
              </div>

              {/* Chat Messages */}
              <div className="flex-1 p-4 overflow-y-auto space-y-3 text-xs">
                {messages.map((m, idx) => (
                  <div key={idx} className={`flex gap-2.5 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {m.role !== 'user' && (
                      <div className="w-7 h-7 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center shrink-0">
                        <Bot className="w-4 h-4" />
                      </div>
                    )}
                    <div className={`max-w-[80%] p-3 rounded-xl whitespace-pre-wrap leading-relaxed ${
                      m.role === 'user' ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-slate-950 border border-slate-800 text-slate-200 rounded-tl-none font-sans'
                    }`}>
                      {m.content}
                    </div>
                    {m.role === 'user' && (
                      <div className="w-7 h-7 rounded-lg bg-slate-800 text-slate-300 flex items-center justify-center shrink-0">
                        <User className="w-4 h-4" />
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Proposed Intent Action Box */}
              {pendingIntent && (
                <div className="p-3 mx-4 mb-2 bg-blue-950/30 border border-blue-500/40 rounded-lg flex items-center justify-between">
                  <div>
                    <div className="text-[10px] font-mono text-blue-400 font-bold uppercase">Proposed Intent Formulated</div>
                    <div className="text-xs text-slate-200 font-semibold">{pendingIntent.item_name} &bull; ₹{pendingIntent.claimed_unit_price_inr.toLocaleString()}</div>
                  </div>
                  <button
                    onClick={handleConfirmAndPayModal}
                    disabled={chatLoading}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition shadow"
                  >
                    <ShieldCheck className="w-4 h-4" /> Confirm & Pay (Modal)
                  </button>
                </div>
              )}

              {/* Chat Input */}
              <form onSubmit={handleSendChatMessage} className="p-3 border-t border-slate-800 flex gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask about monitors, mechanical keyboards, or specifications..."
                  className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                />
                <button
                  type="submit"
                  disabled={chatLoading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium flex items-center gap-1"
                >
                  <Send className="w-3.5 h-3.5" /> Send
                </button>
              </form>
            </div>
          )}

        </div>

        {/* =================================================================== */}
        {/* RIGHT PANE: MCP CATALOG & IMMUTABLE AUDIT LEDGER (5 Cols)           */}
        {/* =================================================================== */}
        <div className="lg:col-span-5 space-y-6">

          {/* Machine-Readable Catalog (MCP) with Chaos Controls */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3">
            <div className="flex justify-between items-center text-xs">
              <span className="font-semibold text-slate-300 flex items-center gap-2 uppercase tracking-wider">
                <Activity className="w-4 h-4 text-emerald-400" /> Catalog & Chaos Controls
              </span>
              <span className="text-[10px] font-mono text-slate-500">Authoritative Ground Truth</span>
            </div>

            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {catalog.map((item) => (
                <div key={item.sku} className="p-2.5 bg-slate-950 border border-slate-800/80 rounded-lg text-xs space-y-1">
                  <div className="flex justify-between font-mono">
                    <span className="text-blue-400 font-semibold">{item.sku}</span>
                    <span className="text-emerald-400 font-bold">₹{item.price_inr.toLocaleString()}</span>
                  </div>
                  <p className="text-slate-300 text-[11px] truncate">{item.name}</p>
                  <div className="flex items-center justify-between pt-1">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${item.stock_quantity > 0 ? 'bg-slate-800 text-slate-300' : 'bg-red-500/20 text-red-400'}`}>
                      Stock: {item.stock_quantity}
                    </span>
                    <div className="space-x-1">
                      <button 
                        onClick={() => triggerChaosStock(item.sku, 0)}
                        className="px-2 py-0.5 bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded text-[10px] font-mono border border-red-500/30"
                      >
                        Chaos: 0
                      </button>
                      <button 
                        onClick={() => triggerChaosStock(item.sku, 10)}
                        className="px-2 py-0.5 bg-slate-800 text-slate-300 hover:bg-slate-700 rounded text-[10px] font-mono"
                      >
                        Reset: 10
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Append-Only Audit Ledger & JSON Inspector */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3 flex flex-col h-[340px]">
            <div className="flex justify-between items-center text-xs pb-2 border-b border-slate-800">
              <span className="font-semibold text-slate-300 flex items-center gap-2 font-mono uppercase tracking-wider">
                <Terminal className="w-4 h-4 text-emerald-400" /> Immutable Audit Ledger
              </span>
              <span className="text-[10px] font-mono text-slate-500">JSON-L Synchronous</span>
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60 pr-1">
              {auditLogs.length === 0 ? (
                <div className="text-slate-600 text-xs text-center pt-16">No audit records yet.</div>
              ) : (
                auditLogs.map((log, idx) => (
                  <div 
                    key={idx} 
                    onClick={() => setSelectedAuditLog(log)}
                    className={`p-2 hover:bg-slate-800/40 rounded-lg cursor-pointer transition flex items-center justify-between text-xs font-mono ${
                      selectedAuditLog?.trace_id === log.trace_id ? 'bg-slate-800/80 border border-slate-700' : ''
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${
                          log.event_type.includes("SUCCESS") || log.event_type.includes("PAID") ? 'bg-emerald-400' :
                          log.event_type.includes("ALERT") || log.event_type.includes("DECLINED") || log.event_type.includes("REJECT") ? 'bg-red-400' : 'bg-blue-400'
                        }`} />
                        <span className="font-semibold text-slate-200">{log.event_type}</span>
                      </div>
                      <div className="text-[10px] text-slate-500">{log.timestamp?.split("T")[1]?.slice(0, 8)} UTC &bull; Trace: {log.trace_id}</div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-600" />
                  </div>
                ))
              )}
            </div>

            {/* Selected JSON Drawer */}
            {selectedAuditLog && (
              <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg text-[10px] font-mono max-h-28 overflow-y-auto space-y-1">
                <div className="flex justify-between text-slate-400 border-b border-slate-800 pb-1 font-bold">
                  <span>RECORD: {selectedAuditLog.trace_id}</span>
                  <span>{selectedAuditLog.event_type}</span>
                </div>
                <pre className="text-slate-300 whitespace-pre-wrap">{JSON.stringify(selectedAuditLog, null, 2)}</pre>
              </div>
            )}
          </div>

        </div>

      </div>
    </div>
  );
}