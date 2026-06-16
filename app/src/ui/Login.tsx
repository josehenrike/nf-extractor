import React, { useState } from "react";

interface LoginProps {
  onLogin: (apiKey: string) => void;
}

export function Login({ onLogin }: LoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [showApiKey, setShowApiKey] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!email || !password || !apiKey) {
      setError("Por favor, preencha todos os campos.");
      return;
    }

    if (email.trim() !== "professor@teste.com" || password !== "teste123") {
      setError("E-mail ou senha incorretos.");
      return;
    }

    if (!apiKey.trim().startsWith("gsk_")) {
      setError("A chave de API do Groq deve iniciar com 'gsk_'.");
      return;
    }

    setLoading(true);
    // Simular carregamento rápido para dar um feedback visual premium
    setTimeout(() => {
      setLoading(false);
      onLogin(apiKey.trim());
    }, 800);
  }

  return (
    <div className="loginContainer">
      <div className="loginCard">
        <div className="loginHeader">
          <div className="loginLogo">
            <span>NF</span>
          </div>
          <h2>NF Extractor</h2>
          <p>Insira suas credenciais e chave de API do Groq para acessar o sistema.</p>
        </div>

        {error && <div className="alertBox loginError">{error}</div>}

        <form onSubmit={handleSubmit} className="loginForm">
          <div className="formGroup">
            <label htmlFor="email">E-mail</label>
            <input
              id="email"
              type="email"
              placeholder="ex: professor@teste.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="loginInput"
              autoComplete="username"
            />
          </div>

          <div className="formGroup">
            <label htmlFor="password">Senha</label>
            <input
              id="password"
              type="password"
              placeholder="ex: teste123"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="loginInput"
              autoComplete="current-password"
            />
          </div>

          <div className="formGroup">
            <label htmlFor="apiKey" className="apiKeyLabel">
              <span>Chave de API do Groq</span>
              <button
                type="button"
                className="toggleShowKeyBtn"
                onClick={() => setShowApiKey(!showApiKey)}
              >
                {showApiKey ? "ocultar" : "mostrar"}
              </button>
            </label>
            <input
              id="apiKey"
              type={showApiKey ? "text" : "password"}
              placeholder="gsk_..."
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="loginInput"
            />
            <span className="inputHint">
              A chave do Groq é necessária para habilitar a extração de notas fiscais e o chat RAG.
            </span>
          </div>

          <button type="submit" className="loginBtn" disabled={loading}>
            {loading ? (
              <>
                <span className="loginSpinner" />
                Acessando...
              </>
            ) : (
              "Acessar Sistema"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
