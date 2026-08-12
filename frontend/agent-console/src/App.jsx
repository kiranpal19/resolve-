import React, { useState, useEffect } from 'react';

export default function App() {
  const [queue, setQueue] = useState([]);
  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [contextPacket, setContextPacket] = useState(null);
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [agentToken, setAgentToken] = useState(null);

  useEffect(() => {
    loginAsAgent();
  }, []);

  const loginAsAgent = async () => {
    try {
      const res = await fetch('/api/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_type: 'agent' })
      });
      const data = await res.json();
      setAgentToken(data.access_token);
      fetchQueue(data.access_token);
    } catch (e) {
      console.error("Agent auth error:", e);
    }
  };

  const fetchQueue = async (token) => {
    try {
      const res = await fetch('/api/agent/queue', {
        headers: { 'Authorization': `Bearer ${token || agentToken}` }
      });
      const data = await res.json();
      if (Array.isArray(data)) {
        setQueue(data);
        if (data.length > 0 && !selectedCaseId) {
          fetchContext(data[0].case_id, token || agentToken);
        }
      }
    } catch (e) {
      console.error("Fetch queue error:", e);
    }
  };

  const fetchContext = async (caseId, token) => {
    setSelectedCaseId(caseId);
    try {
      const res = await fetch(`/api/agent/case/${caseId}/context`, {
        headers: { 'Authorization': `Bearer ${token || agentToken}` }
      });
      const data = await res.json();
      setContextPacket(data);
    } catch (e) {
      console.error("Fetch context error:", e);
    }
  };

  const handleResolve = async (action) => {
    if (!selectedCaseId || !resolutionNotes.trim()) {
      alert("Please enter resolution notes before resolving the case.");
      return;
    }
    setIsSubmitting(true);
    try {
      const res = await fetch(`/api/agent/case/${selectedCaseId}/resolve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${agentToken}`
        },
        body: JSON.stringify({
          action,
          resolution_notes: resolutionNotes,
          override_reason: "Senior servicing specialist manual decision"
        })
      });

      const data = await res.json();
      alert(`Case Resolved! Action logged to Immutable Ledger at Seq #${data.audit_seq}`);
      setResolutionNotes("");
      setContextPacket(null);
      await fetchQueue();

    } catch (e) {
      alert("Error resolving case: " + e.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="console-container">
      {/* Header */}
      <header className="console-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ background: '#D4AF37', color: '#000', padding: '0.3rem 0.6rem', fontWeight: 800, borderRadius: '6px' }}>AMEX</span>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Resolve Human Agent Escalation Console</h2>
        </div>
        <div style={{ fontSize: '0.85rem', color: '#94A3B8' }}>
          Active Specialist: <strong style={{ color: '#FFF' }}>Sarah Connor (ID: agent_7701)</strong>
        </div>
      </header>

      {/* Main Grid */}
      <div className="console-layout">
        {/* Queue Panel */}
        <div className="queue-panel">
          <h3 style={{ fontSize: '1rem', color: '#D4AF37', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem' }}>
            Escalation Queue ({queue.length})
          </h3>
          <div className="queue-list">
            {queue.length === 0 ? (
              <div style={{ color: '#64748B', fontSize: '0.85rem', fontStyle: 'italic', padding: '1rem' }}>
                No active escalated cases in queue. Send an over-ceiling or stolen card request in customer chat to populate.
              </div>
            ) : (
              queue.map((c) => (
                <div
                  key={c.case_id}
                  className={`queue-item ${selectedCaseId === c.case_id ? 'selected' : ''}`}
                  onClick={() => fetchContext(c.case_id)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                    <strong style={{ fontSize: '0.9rem' }}>#{c.case_id.substring(0, 8)}</strong>
                    <span style={{ color: '#F59E0B', fontSize: '0.75rem', fontWeight: 'bold' }}>{c.intent}</span>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#94A3B8' }}>Customer: {c.customer_name}</div>
                  {c.priority_action_taken && (
                    <div style={{ marginTop: '0.4rem', color: '#EF4444', fontSize: '0.75rem', fontWeight: 'bold' }}>
                      ⚡ PRIORITY ACTION: {c.priority_action_taken}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Context Packet & Decision Dashboard */}
        <div className="context-panel">
          {!contextPacket ? (
            <div style={{ color: '#64748B', textAlign: 'center', marginTop: '4rem' }}>
              Select an escalated case from the left queue to view full AI context packet and rule evaluation.
            </div>
          ) : (
            <>
              {/* Top Case Summary */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h2 style={{ fontSize: '1.4rem' }}>Case #{contextPacket.case.case_id.substring(0, 8)}</h2>
                  <p style={{ color: '#94A3B8', fontSize: '0.9rem' }}>
                    Customer: <strong style={{ color: '#FFF' }}>{contextPacket.case.customer_name}</strong> (Account: {contextPacket.case.account_id})
                  </p>
                </div>
                <span style={{ background: 'rgba(245, 158, 11, 0.2)', color: '#F59E0B', padding: '0.5rem 1rem', borderRadius: '8px', fontWeight: 'bold' }}>
                  POLICY ESCALATED
                </span>
              </div>

              {/* Stat Boxes Grid */}
              <div className="context-grid">
                <div className="stat-box">
                  <div style={{ color: '#94A3B8', fontSize: '0.8rem' }}>Matched Policy Rule</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#D4AF37' }}>
                    {contextPacket.policy_decision.rule_matched || 'DEFAULT_ESCALATE'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '0.2rem' }}>
                    {contextPacket.policy_decision.reason}
                  </div>
                </div>

                <div className="stat-box">
                  <div style={{ color: '#94A3B8', fontSize: '0.8rem' }}>Account Risk & Standing</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#38BDF8' }}>
                    Score: {contextPacket.account_info.risk_score} ({contextPacket.account_info.account_standing})
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '0.2rem' }}>
                    Age: {contextPacket.account_info.account_age_months} months
                  </div>
                </div>

                <div className="stat-box">
                  <div style={{ color: '#94A3B8', fontSize: '0.8rem' }}>Priority Action Status</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: contextPacket.policy_decision.priority_action_taken ? '#EF4444' : '#10B981' }}>
                    {contextPacket.policy_decision.priority_action_taken || 'NONE'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '0.2rem' }}>
                    {contextPacket.policy_decision.priority_action_taken ? 'Immediate freeze executed' : 'Standard review queue'}
                  </div>
                </div>
              </div>

              {/* Context Snapshot JSON */}
              <div style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '1rem' }}>
                <h4 style={{ fontSize: '0.9rem', color: '#38BDF8', marginBottom: '0.5rem' }}>Extracted Entities & Context Snapshot</h4>
                <pre style={{ color: '#A7F3D0', fontSize: '0.8rem', overflowX: 'auto', background: '#050B14', padding: '0.75rem', borderRadius: '8px' }}>
                  {JSON.stringify(contextPacket.context_snapshot, null, 2)}
                </pre>
              </div>

              {/* Action Resolution Form */}
              <div className="action-bar">
                <h4 style={{ fontSize: '0.95rem', color: '#D4AF37' }}>Human Servicing Decision (Appends to Immutable Audit Ledger)</h4>
                <textarea
                  style={{ width: '100%', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.1)', color: '#FFF', padding: '0.75rem', borderRadius: '8px', height: '70px', outline: 'none' }}
                  placeholder="Enter mandatory resolution notes and rationale..."
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                />
                <div style={{ display: 'flex', gap: '1rem' }}>
                  <button className="btn-approve" disabled={isSubmitting} onClick={() => handleResolve("APPROVE_OVERRULE")}>
                    Approve Overrule
                  </button>
                  <button className="btn-reject" disabled={isSubmitting} onClick={() => handleResolve("REJECT")}>
                    Reject Request
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
