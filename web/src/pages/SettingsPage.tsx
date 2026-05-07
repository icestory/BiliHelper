import { useEffect, useState } from "react";
import {
  listCredentials, createCredential, deleteCredential, setDefaultCredential,
  listBilibiliCredentials, createBilibiliCredential, deleteBilibiliCredential, enableBilibiliCredential,
} from "../api/credentials";
import type { ApiCredentialResponse, BilibiliCredentialResponse } from "../types";

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

  // ============ B 站 Cookie 配置 ============
  const [biliCreds, setBiliCreds] = useState<BilibiliCredentialResponse[]>([]);
  const [biliLoading, setBiliLoading] = useState(true);
  const [showBiliForm, setShowBiliForm] = useState(false);
  const [biliSessdata, setBiliSessdata] = useState("");
  const [biliJct, setBiliJct] = useState("");
  const [biliBuvid3, setBiliBuvid3] = useState("");
  const [biliSubmitting, setBiliSubmitting] = useState(false);

  const fetchBiliCreds = async () => {
    setBiliLoading(true);
    try {
      const res = await listBilibiliCredentials();
      if (res.ok) setBiliCreds(await res.json());
    } catch {
      setError("B 站 Cookie 加载失败");
    } finally {
      setBiliLoading(false);
    }
  };

  useEffect(() => { fetchBiliCreds(); }, []);

  const handleBiliCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!biliSessdata.trim() || !biliJct.trim()) return;
    setBiliSubmitting(true);
    try {
      const res = await createBilibiliCredential({
        sessdata: biliSessdata.trim(),
        bili_jct: biliJct.trim(),
        buvid3: biliBuvid3.trim() || undefined,
        enabled: biliCreds.length === 0,
      });
      if (res.ok) {
        const newCred = await res.json();
        setBiliCreds(prev => [...prev, newCred]);
        setShowBiliForm(false);
        setBiliSessdata("");
        setBiliJct("");
        setBiliBuvid3("");
      }
    } catch {
      setError("B 站 Cookie 创建失败");
    } finally {
      setBiliSubmitting(false);
    }
  };

  const handleBiliDelete = async (id: number) => {
    if (!confirm("确定删除此 Cookie 配置？")) return;
    const res = await deleteBilibiliCredential(id);
    if (res.ok) setBiliCreds(prev => prev.filter(c => c.id !== id));
  };

  const handleBiliEnable = async (id: number) => {
    const res = await enableBilibiliCredential(id);
    if (res.ok) fetchBiliCreds();
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

      {/* ============ B 站 Cookie 配置 ============ */}
      <hr style={{ margin: "2rem 0" }} />
      <h2>B 站 Cookie 配置</h2>
      <p style={{ fontSize: "0.85rem", color: "#888" }}>
        用于海外服务器或风控绕过。从浏览器登录 B 站后复制 Cookie 中的 SESSDATA、bili_jct、buvid3 三个值即可。
      </p>

      <button onClick={() => setShowBiliForm(!showBiliForm)}>
        {showBiliForm ? "取消" : "+ 添加 B 站 Cookie"}
      </button>

      {showBiliForm && (
        <form onSubmit={handleBiliCreate} style={{ margin: "1rem 0", padding: "1rem", border: "1px solid #ddd", borderRadius: 8 }}>
          <div style={{ marginBottom: "0.5rem" }}>
            <label>SESSDATA *</label>
            <input type="text" value={biliSessdata} onChange={e => setBiliSessdata(e.target.value)} placeholder="从 B 站 Cookie 复制" style={{ width: "100%", padding: "0.3rem" }} required />
          </div>
          <div style={{ marginBottom: "0.5rem" }}>
            <label>bili_jct *</label>
            <input type="text" value={biliJct} onChange={e => setBiliJct(e.target.value)} placeholder="从 B 站 Cookie 复制" style={{ width: "100%", padding: "0.3rem" }} required />
          </div>
          <div style={{ marginBottom: "0.5rem" }}>
            <label>buvid3（可选）</label>
            <input type="text" value={biliBuvid3} onChange={e => setBiliBuvid3(e.target.value)} placeholder="从 B 站 Cookie 复制" style={{ width: "100%", padding: "0.3rem" }} />
          </div>
          <button type="submit" disabled={biliSubmitting || !biliSessdata.trim() || !biliJct.trim()}>
            {biliSubmitting ? "创建中..." : "创建"}
          </button>
        </form>
      )}

      {biliLoading && <p>加载中...</p>}

      {!biliLoading && biliCreds.length === 0 && (
        <p style={{ color: "#888" }}>未配置 B 站 Cookie，海外服务器可能无法访问 B 站。</p>
      )}

      {biliCreds.map(c => (
        <div key={c.id} style={{ padding: "0.75rem", margin: "0.5rem 0", border: "1px solid #eee", borderRadius: 8, background: c.enabled ? "#e3f2fd" : "white" }}>
          <strong>Cookie 凭证 #{c.id}</strong>
          {c.enabled && <span style={{ color: "#1976d2", marginLeft: "0.5rem", fontSize: "0.85rem" }}>[启用中]</span>}
          <div style={{ fontSize: "0.9rem", color: "#666" }}>
            <span>SESSDATA: {c.sessdata_masked}</span>
            <span style={{ marginLeft: "1rem" }}>bili_jct: {c.bili_jct_masked}</span>
            {c.buvid3_masked && <span style={{ marginLeft: "1rem" }}>buvid3: {c.buvid3_masked}</span>}
            <span style={{ marginLeft: "1rem", fontSize: "0.8rem" }}>更新于: {new Date(c.updated_at).toLocaleString()}</span>
          </div>
          <div style={{ marginTop: "0.25rem" }}>
            {!c.enabled && (
              <button onClick={() => handleBiliEnable(c.id)} style={{ marginRight: "0.5rem", fontSize: "0.85rem" }}>启用</button>
            )}
            <button onClick={() => handleBiliDelete(c.id)} style={{ fontSize: "0.85rem", color: "red" }}>删除</button>
          </div>
        </div>
      ))}
    </div>
  );
}
