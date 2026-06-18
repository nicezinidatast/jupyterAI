"""백업 실패 알림과 분기별 접근권한 리포트 발송용 비동기 SMTP 어댑터.

외부 SMTP 서버와의 통신 세부 사항을 캡슐화해 서비스 계층이 이메일 전송 방식에
의존하지 않도록 한다. 서비스는 SmtpAdapter 인터페이스만 알면 된다.

aiosmtplib를 사용하는 이유:
- FastAPI/asyncio 이벤트 루프를 블로킹하지 않는 비동기 SMTP 클라이언트이기 때문.
- 표준 라이브러리 smtplib는 동기식이라 async 컨텍스트에서 스레드 풀을 써야 하는
  번거로움이 있다.

오류 처리 전략:
- SMTP 예외(연결 실패, 인증 오류, 타임아웃)는 모두 Err(DomainError.EXTERNAL_UNAVAILABLE)로
  변환해 반환한다. 상위 호출자가 재시도 여부를 결정한다.
- 예외를 전파하지 않는 이유: 이메일 전송 실패가 핵심 도메인 로직(백업 실행 등)을
  롤백해서는 안 되기 때문이다.
"""

from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result


class SmtpAdapter:
    """aiosmtplib 기반 비동기 SMTP 발송 어댑터.

    인스턴스당 하나의 SMTP 서버 연결 설정을 보유한다.
    연결을 재사용하지 않고 매 send() 호출마다 새 연결을 맺는다.
    이는 장시간 idle 연결을 유지하다 서버 측에서 끊기는 문제를 피하기 위해서다.

    Args:
        host: SMTP 서버 호스트명 또는 IP.
        port: SMTP 포트. 기본값 25(평문). TLS 사용 시 보통 465 또는 587.
        use_tls: True이면 aiosmtplib가 SMTPS(암호화) 연결을 사용한다.
    """

    def __init__(self, *, host: str, port: int = 25, use_tls: bool = False) -> None:
        self._host = host
        self._port = port
        self._use_tls = use_tls

    async def send(
        self, *, sender: str, recipients: list[str], subject: str, body: str
    ) -> Result[None, DomainError]:
        """이메일 한 건을 발송한다.

        EmailMessage 객체를 생성해 aiosmtplib.send()로 전달한다.
        표준 라이브러리 email.message를 사용하므로 헤더 인코딩이 RFC 5322를 따른다.

        Args:
            sender: 발신자 이메일 주소 (From 헤더).
            recipients: 수신자 이메일 주소 목록 (To 헤더; 쉼표+공백으로 결합).
            subject: 메일 제목.
            body: 본문 텍스트(plain text).

        Returns:
            Ok(None): 발송 성공.
            Err(DomainError.EXTERNAL_UNAVAILABLE): SMTP 오류 발생 시.
        """
        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.set_content(body)
        try:
            await aiosmtplib.send(
                msg, hostname=self._host, port=self._port, use_tls=self._use_tls
            )
            return Ok(None)
        except aiosmtplib.SMTPException:
            # 연결 실패·인증 오류·타임아웃 등 모든 SMTP 예외를 EXTERNAL_UNAVAILABLE로 통일한다.
            # 세부 오류를 상위로 전파하지 않는 이유: 이메일 실패가 핵심 트랜잭션을
            # 롤백하면 안 되기 때문이다.
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
