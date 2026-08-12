import React, { useState, useEffect, useRef } from 'react';

const DEMO_ACCOUNTS = [
  { id: "acc_good_customer", name: "Alex Mercer (Good Standing)", limit: "$10,000", fee: "$35.00" },
  { id: "acc_cooldown_customer", name: "Jordan Lee (Cooldown Escalation)", limit: "$5,000", fee: "$40.00" },
  { id: "acc_high_risk", name: "Taylor Swift (High Risk / Stolen)", limit: "$2,000", fee: "$120.00" }
];

export default function App() {
  const [selectedAccount, setSelectedAccount] = useState(DEMO_ACCOUNTS[0]);
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      sender: "agent",
      text: "Hello Alex! I am Resolve, your 24/7 AI Credit Card Servicing Assistant powered by deterministic policy verification. How may I assist you today?"
    }
  ]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [latestCaseId, setLatestCaseId] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [chainIntegrity, setChainIntegrity] = useState({ valid: true, total: 0 });

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    verifyChainIntegrity();
  }, []);

  const verifyChainIntegrity = async () => {
    try {
      const res = await fetch('/audit/verify');
      const data = await res.json();
      setChainIntegrity(data);
    } catch (e) {
      console.error("Audit verification error:", e);
    }
  };

  const fetchAuditLogs = async (caseId) => {
    try {
      const res = await fetch(`/audit/case/${caseId}`);
      const data = await res.json();
      if (data.audit_trail) {
        setAuditLogs(data.audit_trail);
      }
    } catch (e) {
      console.error("Error fetching audit trail:", e);
    }
  };

  const handleSend = async (textToSend) => {
    const text = textToSend || inputText;
    if (!text.trim() || isLoading) return;

    const userMsg = { id: Date.now().toString(), sender: "user", text };
    setMessages(prev => [...prev, userMsg]);
    setInputText("");
    setIsLoading(true);

    try {
      const res = await fetch('/api/conversation/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          account_id: selectedAccount.id
        })
      });

      const data = await res.json();

      const agentMsg = {
        id: (Date.now() + 1).toString(),
        sender: "agent",
        text: data.agent_response,
        caseId: data.case_id,
        policy: data.policy_decision,
        status: data.status,
        audit: data.audit_ledger
      };

      setMessages(prev => [...prev, agentMsg]);
      setLatestCaseId(data.case_id);

      if (data.case_id) {
        await fetchAuditLogs(data.case_id);
      }
      await verifyChainIntegrity();

    } catch (err) {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        sender: "agent",
        text: "Error communicating with servicing server. Please verify system connection."
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="header">
        <div className="brand">
          <span className="brand-badge">AMEX</span>
          <span className="brand-title">Resolve Card Servicing Portal</span>
        </div>

        <div className="user-selector">
          {DEMO_ACCOUNTS.map(acc => (
            <button
              key={acc.id}
              className={`user-btn ${selectedAccount.id === acc.id ? 'active' : ''}`}
              onClick={() => {
                setSelectedAccount(acc);
                setMessages([{
                  id: Date.now().toString(),
                  sender: "agent",
                  text: `Switched context to ${acc.name}. How can I help with this account?`
                }]);
              }}
            >
              {acc.name.split(' ')[0]}
            </button>
          ))}
        </div>
      </header>

      {/* Main Layout Grid */}
      <div className="main-layout">
        {/* Chat Panel */}
        <div className="chat-panel">
          <div className="messages-area">
            {messages.map((m) => (
              <div key={m.id} className={`message-bubble message-${m.sender}`}>
                <p>{m.text}</p>
                {m.policy && (
                  <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.1)', fontSize: '0.8rem' }}>
                    <span style={{
                      padding: '0.2rem 0.5rem',
                      borderRadius: '4px',
                      fontWeight: 'bold',
                      backgroundColor: m.policy.outcome === 'APPROVE' ? 'rgba(16, 185, 129, 0.2)' : m.policy.outcome === 'ESCALATE' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                      color: m.policy.outcome === 'APPROVE' ? '#10B981' : m.policy.outcome === 'ESCALATE' ? '#F59E0B' : '#EF4444'
                    }}>
                      POLICY: {m.policy.outcome} ({m.policy.matched_rule_id || 'FAIL_CLOSED_DEFAULT'})
                    </span>
                    {m.audit && (
                      <span style={{ marginLeft: '0.5rem', color: '#94A3B8', fontFamily: 'monospace' }}>
                        Ledger Seq #{m.audit.seq}
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="message-bubble message-agent">
                <p>Evaluating policy rules & checking audit chain...</p>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Action Chips */}
          <div className="quick-actions">
            <button className="action-chip" onClick={() => handleSend("Can you reverse my $35 late fee?")}>
              Reverse $35 Late Fee
            </button>
            <button className="action-chip" onClick={() => handleSend("I want a 20% credit limit increase.")}>
              Request 20% Credit Limit Increase
            </button>
            <button className="action-chip" onClick={() => handleSend("My card was stolen in the subway this morning.")}>
              Report Card Stolen (Freeze)
            </button>
            <button className="action-chip" onClick={() => handleSend("I need a replacement for my damaged card.")}>
              Replace Damaged Card
            </button>
          </div>

          {/* Input Bar */}
          <div className="input-area">
            <input
              type="text"
              className="chat-input"
              placeholder="Ask Resolve anything about fees, limits, or replacement cards..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            />
            <button className="send-btn" onClick={() => handleSend()}>Send</button>
          </div>
        </div>

        {/* Right Side Panel: Immutable Audit Ledger Tracker */}
        <div className="side-panel">
          <div className="audit-card">
            <div className="audit-header">
              <span className="audit-title">⚡ Cryptographic Audit Ledger</span>
              <span className={`verify-badge ${chainIntegrity.valid ? 'valid' : ''}`}>
                {chainIntegrity.valid ? 'CHAIN VERIFIED 100%' : 'CHAIN BROKEN'}
              </span>
            </div>

            <div style={{ fontSize: '0.8rem', color: '#94A3B8', marginBottom: '0.75rem' }}>
              Every policy evaluation is hash-chained to Postgres before action execution.
            </div>

            <div className="audit-log-list">
              {auditLogs.length === 0 ? (
                <div style={{ color: '#64748B', fontSize: '0.85rem', fontStyle: 'italic', padding: '1rem' }}>
                  Send a request to observe real-time SHA-256 hash-chain ledger entries.
                </div>
              ) : (
                auditLogs.map((log) => (
                  <div key={log.seq} className="audit-item">
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                      <strong style={{ color: '#FFF' }}>Seq #{log.seq}: {log.action}</strong>
                      <span style={{ color: '#10B981', fontWeight: 'bold' }}>{log.outcome}</span>
                    </div>
                    <div style={{ color: '#94A3B8', fontSize: '0.75rem' }}>Rule: {log.matched_rule_id}</div>
                    <div style={{ marginTop: '0.25rem' }}>
                      <span style={{ color: '#64748B' }}>Hash: </span>
                      <span className="hash-text">{log.record_hash?.substring(0, 24)}...</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
