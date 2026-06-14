import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { KeyRound, LogIn, Mail, UserPlus } from "lucide-react";

import { api } from "../api/client";
import { ErrorBanner } from "../components/ErrorBanner";
import { IconButton } from "../components/IconButton";
import { useAuth } from "../context/AuthContext";

type AuthPageProps = {
  mode: "login" | "register" | "reset";
};

export function AuthPage({ mode }: AuthPageProps) {
  const navigate = useNavigate();
  const { login, register } = useAuth();
  const [identifier, setIdentifier] = useState("");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [nickname, setNickname] = useState("");
  const [password, setPassword] = useState("");
  const [resetCode, setResetCode] = useState("");
  const [resetPassword, setResetPassword] = useState("");
  const [resetPasswordConfirm, setResetPasswordConfirm] = useState("");
  const [resetCodeSent, setResetCodeSent] = useState(false);
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const isRegister = mode === "register";
  const isReset = mode === "reset";

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setNotice("");

    try {
      if (isReset) {
        if (!resetCodeSent) {
          await api.post<{ detail: string }>("/auth/password-reset/request/", { email });
          setResetCodeSent(true);
          setNotice("인증 코드를 이메일로 보냈습니다.");
          return;
        }
        if (resetPassword !== resetPasswordConfirm) {
          throw new Error("새 비밀번호가 서로 다릅니다.");
        }
        await api.post<{ detail: string }>("/auth/password-reset/confirm/", {
          email,
          code: resetCode,
          new_password: resetPassword
        });
        setNotice("비밀번호가 변경되었습니다. 새 비밀번호로 로그인하세요.");
        setResetCode("");
        setResetPassword("");
        setResetPasswordConfirm("");
        return;
      }

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
          <span>{isReset ? "비밀번호 찾기" : isRegister ? "계정 만들기" : "로그인"}</span>
        </div>

        <ErrorBanner error={error} />
        {notice ? <div className="success-banner">{notice}</div> : null}

        <form className="form-grid" onSubmit={handleSubmit}>
          {isReset ? (
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
              {resetCodeSent ? (
                <>
                  <label>
                    인증 코드
                    <input
                      value={resetCode}
                      onChange={(event) => setResetCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                      required
                      inputMode="numeric"
                      maxLength={6}
                    />
                  </label>
                  <label>
                    새 비밀번호
                    <input
                      type="password"
                      value={resetPassword}
                      onChange={(event) => setResetPassword(event.target.value)}
                      required
                      minLength={8}
                      autoComplete="new-password"
                    />
                  </label>
                  <label>
                    새 비밀번호 확인
                    <input
                      type="password"
                      value={resetPasswordConfirm}
                      onChange={(event) => setResetPasswordConfirm(event.target.value)}
                      required
                      minLength={8}
                      autoComplete="new-password"
                    />
                  </label>
                </>
              ) : null}
            </>
          ) : isRegister ? (
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

          {!isReset ? (
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
          ) : null}

          <IconButton
            icon={isReset ? (resetCodeSent ? KeyRound : Mail) : isRegister ? UserPlus : LogIn}
            label={
              pending
                ? "처리 중"
                : isReset
                  ? resetCodeSent
                    ? "비밀번호 변경"
                    : "인증 코드 받기"
                  : isRegister
                    ? "가입"
                    : "로그인"
            }
            disabled={pending}
            type="submit"
          />
        </form>

        <div className="auth-switch">
          {isReset ? (
            <Link to="/login">로그인으로 이동</Link>
          ) : isRegister ? (
            <Link to="/login">로그인으로 이동</Link>
          ) : (
            <>
              <Link to="/register">회원가입으로 이동</Link>
              <Link to="/forgot-password">비밀번호 찾기</Link>
            </>
          )}
        </div>
      </section>
    </main>
  );
}
