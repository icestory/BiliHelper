import { useEffect, useState } from "react";
import { listCredentials, createCredential, deleteCredential, setDefaultCredential } from "../api/credentials";
import type { ApiCredentialResponse } from "../types";

export default function SettingsPage() {
  const [creds, setCreds] = useState<ApiCredentialResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);

  // form state
  const [provider, setProvider] = useState("openai");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchCreds = async () => {
    setLoading(true);
    try {
      const res = await listCredentials();
      if (res.ok) setCreds(await res.json());
    } catch {
      setError("加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCreds(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim()) return;
    setSubmitting(true);
    try {
      const res = await createCredential({
        provider,
        api_key: apiKey.trim(),
        api_base_url: baseUrl.trim() || undefined,
        default_model: model.trim() || undefined,
        is_default: creds.length === 0,
      });
      if (res.ok) {
        const newCred = await res.json();
        setCreds(prev => [...prev, newCred]);
        setShowForm(false);
        setApiKey("");
        setBaseUrl("");
        setModel("");
      }
    } catch {
      setError("创建失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除此配置？")) return;
    const res = await deleteCredential(id);
    if (res.ok) setCreds(prev => prev.filter(c => c.id !== id));
  };

  const handleSetDefault = async (id: number) => {
    const res = await setDefaultCredential(id);
    if (res.ok) fetchCreds();
  };

  return (
    <div>
      <h1>LLM API 配置</h1>
      {error && <p style={{ color: "red" }}>{error}</p>}

      <button onClick={() => setShowForm(!showForm)}>
        {showForm ? "取消" : "+ 添加 API Key"}
      </button>

      {showForm && (
        <form onSubmit={handleCreate} style={{ margin: "1rem 0", padding: "1rem", border: "1px solid #ddd", borderRadius: 8 }}>
          <div style={{ marginBottom: "0.5rem" }}>
            <label>供应商</label>
            <select value={provider} onChange={e => setProvider(e.target.value)}>
              <option value="openai">OpenAI</option>
              <option value="deepseek">DeepSeek</option>
              <option value="qwen">通义千问 (Qwen)</option>
              <option value="ollama">Ollama (本地)</option>
              <option value="custom">自定义</option>
            </select>
          </div>
          <div style={{ marginBottom: "0.5rem" }}>
            <label>API Key *</label>
            <input type="password" value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder="sk-..." style={{ width: "100%", padding: "0.3rem" }} required />
          </div>
          <div style={{ marginBottom: "0.5rem" }}>
            <label>Base URL（可选，留空用默认）</label>
            <input type="text" value={baseUrl} onChange={e => setBaseUrl(e.target.value)} placeholder="https://api.openai.com/v1" style={{ width: "100%", padding: "0.3rem" }} />
          </div>
          <div style={{ marginBottom: "0.5rem" }}>
            <label>默认模型（可选）</label>
            <input type="text" value={model} onChange={e => setModel(e.target.value)} placeholder="gpt-4o-mini" style={{ width: "100%", padding: "0.3rem" }} />
          </div>
          <button type="submit" disabled={submitting || !apiKey.trim()}>
            {submitting ? "创建中..." : "创建"}
          </button>
        </form>
      )}

      {loading && <p>加载中...</p>}

      {!loading && creds.length === 0 && (
        <p>还没有配置 API Key，请添加一个。</p>
      )}

      {creds.map(c => (
        <div key={c.id} style={{ padding: "0.75rem", margin: "0.5rem 0", border: "1px solid #eee", borderRadius: 8, background: c.is_default ? "#e8f5e9" : "white" }}>
          <strong>{c.provider}</strong>
          {c.is_default && <span style={{ color: "green", marginLeft: "0.5rem", fontSize: "0.85rem" }}>[默认]</span>}
          <div style={{ fontSize: "0.9rem", color: "#666" }}>
            <span>Key: {c.api_key_masked}</span>
            {c.default_model && <span> | 模型: {c.default_model}</span>}
            {c.api_base_url && <span> | {c.api_base_url}</span>}
          </div>
          <div style={{ marginTop: "0.25rem" }}>
            {!c.is_default && (
              <button onClick={() => handleSetDefault(c.id)} style={{ marginRight: "0.5rem", fontSize: "0.85rem" }}>设为默认</button>
            )}
            <button onClick={() => handleDelete(c.id)} style={{ fontSize: "0.85rem", color: "red" }}>删除</button>
          </div>
        </div>
      ))}
    </div>
  );
}
