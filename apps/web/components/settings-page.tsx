"use client";

import {
  ArrowLeft,
  Database,
  Globe,
  Key,
  Server,
  Settings,
  Zap,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type SettingItem = {
  label: string;
  value: string;
  icon: typeof Server;
  description?: string;
};

export function SettingsPage({ onBack }: { onBack: () => void }) {
  const settings: SettingItem[] = [
    {
      label: "API 地址",
      value: API_BASE,
      icon: Globe,
      description: "后端 API 服务地址",
    },
    {
      label: "数据库",
      value: "PostgreSQL",
      icon: Database,
      description: "主数据库",
    },
    {
      label: "缓存",
      value: "Redis",
      icon: Database,
      description: "事件缓存和状态存储",
    },
    {
      label: "向量库",
      value: "Milvus",
      icon: Database,
      description: "知识检索向量存储",
    },
    {
      label: "LLM 提供商",
      value: "DeepSeek",
      icon: Server,
      description: "大语言模型服务",
    },
    {
      label: "嵌入模型",
      value: "SiliconFlow",
      icon: Server,
      description: "文本嵌入服务",
    },
  ];

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark">
            <Zap size={20} />
          </span>
          <div>
            <strong>pWPS Agent</strong>
            <span>系统设置</span>
          </div>
        </div>
        <button className="ghost-button" onClick={onBack} style={{ width: "auto" }}>
          <ArrowLeft size={16} />
          返回
        </button>
      </header>

      <section className="settings-container">
        <div className="settings-header">
          <Settings size={24} />
          <h1>系统设置</h1>
          <p>当前系统配置信息（只读）</p>
        </div>

        <div className="settings-grid">
          {settings.map((item) => (
            <div key={item.label} className="settings-card">
              <div className="settings-card-icon">
                <item.icon size={20} />
              </div>
              <div className="settings-card-content">
                <h3>{item.label}</h3>
                <p className="settings-value">{item.value}</p>
                {item.description && (
                  <small>{item.description}</small>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="settings-section">
          <h2>
            <Key size={18} />
            API 密钥
          </h2>
          <p className="settings-note">
            API 密钥通过环境变量配置，不在此页面显示。
            请在 <code>.env</code> 文件中设置以下变量：
          </p>
          <div className="settings-code">
            <pre>{`LLM_API_KEY=your-deepseek-api-key
EMBEDDING_API_KEY=your-siliconflow-api-key
RERANKER_API_KEY=your-siliconflow-api-key`}</pre>
          </div>
        </div>

        <div className="settings-section">
          <h2>
            <Server size={18} />
            系统信息
          </h2>
          <div className="settings-info">
            <div>
              <strong>版本</strong>
              <span>0.1.0</span>
            </div>
            <div>
              <strong>Schema 版本</strong>
              <span>1.0.0</span>
            </div>
            <div>
              <strong>工作流版本</strong>
              <span>0.3.0</span>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
