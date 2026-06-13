import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LogIn, UserPlus } from "lucide-react";

import { ErrorBanner } from "../components/ErrorBanner";
import { IconButton } from "../components/IconButton";
import { useAuth } from "../context/AuthContext";

type AuthPageProps = {
  mode: "login" | "register";
};

export function AuthPage({ mode }: AuthPageProps) {
  const navigate = useNavigate();
  const { login, register } = useAuth();
  const [identifier, setIdentifier] = useState("");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [nickname, setNickname] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const isRegister = mode === "register";

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);

    try {
      if (isRegister) {
        await register({ email, username, nickname, password });
      } else {
        await login({ identifier, password });
      }
      navigate("/", { replace: true });
    } catch (submitError) {
      setError(submitError);
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="auth-screen">
      <section className="auth-panel">
        <div className="auth-brand">
          <strong>Home Inventory Map</strong>
          <span>{isRegister ? "계정 만들기" : "로그인"}</span>
        </div>

        <ErrorBanner error={error} />

        <form className="form-grid" onSubmit={handleSubmit}>
          {isRegister ? (
            <>
              <label>
                이메일
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  autoComplete="email"
                />
              </label>
              <label>
                사용자 이름
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  autoComplete="username"
                />
              </label>
              <label>
                닉네임
                <input value={nickname} onChange={(event) => setNickname(event.target.value)} />
              </label>
            </>
          ) : (
            <label>
              이메일 또는 사용자 이름
              <input
                value={identifier}
                onChange={(event) => setIdentifier(event.target.value)}
                required
                autoComplete="username"
              />
            </label>
          )}

          <label>
            비밀번호
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={8}
              autoComplete={isRegister ? "new-password" : "current-password"}
            />
          </label>

          <IconButton
            icon={isRegister ? UserPlus : LogIn}
            label={pending ? "처리 중" : isRegister ? "가입" : "로그인"}
            disabled={pending}
            type="submit"
          />
        </form>

        <div className="auth-switch">
          {isRegister ? (
            <Link to="/login">로그인으로 이동</Link>
          ) : (
            <Link to="/register">회원가입으로 이동</Link>
          )}
        </div>
      </section>
    </main>
  );
}
