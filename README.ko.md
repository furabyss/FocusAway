# FocusAway

FocusAway는 로컬 또는 소규모 그룹용 LLM 서비스를 운영하기 위한 OpenAI 호환 미들웨어입니다.

구조는 다음과 같습니다.

```text
프론트엔드 -> FocusAway -> OpenAI 호환 업스트림 백엔드
```

실제 모델 실행은 업스트림 백엔드가 담당합니다. FocusAway는 사용자 계정, 사용자별 API 키, 모델 접근 정책, 할당량 차감, 웹 관리 패널을 담당합니다.

현재 버전 푸터:

```text
FocusAway v1.0.4, ⓒ 2026 Fur-Abyss.
```

## 주요 기능

- 사용자에게 OpenAI 호환 API 제공.
- OpenAI 호환 업스트림 백엔드 연결.
- 로그인, 회원가입, 대시보드, 관리자 기능을 제공하는 웹 패널.
- 최초 가입 계정 자동 관리자 지정.
- 영어 소문자와 숫자로 이루어진 접속 아이디.
- 사용자별 FocusAway API 키 발급.
- SQLite 기반 사용자, 세션, 티어, 모델 정책, 할당량 기록, 사용 기록 관리.
- 티어 기반 모델 접근 제어와 티어별 주간 충전량.
- 관리자 전용 모델 설정.
- 업스트림 모델 목록 수동 새로고침.
- 모델별 1회 요청 비용 설정, 소수점 둘째 자리까지 저장.
- 설정된 타임존 기준 매주 월요일 0시 주간 잔액 초기화.
- 전체 회원 또는 특정 회원 대상 보너스 잔액 지급.
- 모델 카드에 메타데이터, 필요 티어, 복사 버튼, 최근 24시간 호출 차트 표시.
- `focusaway-config.json`의 업스트림 API 키 암호화 저장.
- 크로스플랫폼 Python 서버 코어.
- 로컬 편의용 `tkinter` 데스크톱 런처.

## 파일 구성

- `app.py`: 서버 실행 진입점.
- `launcher.py`: 로컬 데스크톱 런처.
- `FocusAway.command`: macOS 실행 도우미.
- `FocusAway.sh`: Linux/macOS 셸 실행 도우미.
- `FocusAway.bat`: Windows 실행 도우미.
- `focusaway-config.example.json`: 예시 설정 파일.
- `focusaway/`: 애플리케이션 패키지.
- `focusaway/config.py`: 설정 로드/저장과 업스트림 키 암호화 처리.
- `focusaway/db.py`: SQLite 스키마, 마이그레이션, 데이터 접근.
- `focusaway/server.py`: 웹 패널, API 라우트, 인증, 할당량, 프록시, 렌더링.
- `focusaway/upstream.py`: 업스트림 HTTP 클라이언트.
- `focusaway/secret.py`: 업스트림 API 키 암호화 유틸리티.

## 요구 사항

- Python 3.10 이상 권장.
- 서버 코어는 별도 Python 패키지 설치 없이 표준 라이브러리만 사용합니다.
- 런처는 Python 내장 `tkinter`를 사용합니다. 일부 Linux 배포판은 Tk를 별도로 설치해야 할 수 있습니다.
- 실제 모델 추론을 위해 OpenAI 호환 업스트림 백엔드가 필요합니다.

## 관리자 빠른 시작

1. OpenAI 호환 업스트림 백엔드를 먼저 실행합니다.

2. FocusAway를 실행합니다.

```bash
python3 launcher.py
```

또는 서버만 직접 실행합니다.

```bash
python3 app.py
```

3. 런처에서 다음 항목을 설정합니다.

- `Host`: 로컬 전용이면 보통 `127.0.0.1`.
- `Port`: 기본값 `8787`.
- `Upstream Base URL`: 예를 들어 `http://127.0.0.1:11434`.
- `Upstream API Prefix`: 보통 `/v1`.
- `Upstream Models Path`: 보통 `/v1/models`.
- `Upstream API Key`: 업스트림 백엔드에서 미리 만든 키. 필요 없으면 비워둘 수 있습니다.
- `Upstream Auth Mode`: 보통 `bearer`, `header`, `x-api-key`, `none` 중 하나.

4. 웹 패널을 엽니다.

```text
http://127.0.0.1:8787
```

5. 첫 계정을 생성합니다. 최초 가입 계정은 관리자가 됩니다.

6. 관리자 패널에서 백엔드 모델 새로고침을 실행합니다.

7. 티어, 티어별 주간 충전량, 모델별 비용, 모델별 접근 권한, 모델 메타데이터 override를 설정합니다.

8. 사용자에게 FocusAway API 주소와 각자의 API 키 사용법을 안내합니다.

## 일반 사용자 빠른 시작

1. 관리자가 알려준 웹 패널 주소에서 회원가입 또는 로그인을 합니다.

2. 대시보드를 엽니다.

3. 다음 항목을 확인합니다.

- 내 티어
- 남은 프리미엄 요청
- 사용 가능한 모델 목록
- 모델별 비용과 필요 티어
- 내 전용 API 키
- API 주소

4. 사용하는 프론트엔드에 FocusAway API 주소와 내 전용 API 키를 입력합니다.

일반적인 API 주소:

```text
http://127.0.0.1:8787/v1
```

프론트엔드가 자동으로 `/v1`을 붙인다면 다음처럼 입력합니다.

```text
http://127.0.0.1:8787
```

인증 헤더:

```http
Authorization: Bearer fk_...
```

프론트엔드에는 업스트림 백엔드 API 키를 넣지 마세요. FocusAway에서 발급한 사용자별 API 키만 사용합니다.

## 관리자 설명서

### 모델 관리

업스트림 백엔드의 모델 구성이 바뀌면 `관리자 패널 -> 백엔드에서 모델 새로고침`을 실행합니다.

업스트림에서 사라진 모델은 새로고침 시 FocusAway의 모델 정책 저장소에서도 제거됩니다. 계속 존재하는 모델의 기존 정책은 보존됩니다.

모델 동기화는 관리자 패널에서만 수동으로 실행됩니다. 사용자 API 요청에 빈 모델명이나 등록되지 않은 모델명이 들어와도 업스트림 모델 목록을 자동 조회하지 않습니다. 관리자 패널의 `서비스 설정 -> 기본 모델`을 지정하면 이런 요청은 기본 모델로 대체되며, 기본 모델의 티어 접근 정책과 요청 비용이 그대로 적용됩니다. 기본 모델이 업스트림 새로고침에서 제거되면 설정도 자동 해제됩니다.

모델별로 설정 가능한 항목:

- 1회 요청 비용
- 관리자 전용 또는 최소 필요 티어
- 모델 종류: 서버 기본값, `LLM`, `VLM`
- 커스텀 컨텍스트 윈도우
- 커스텀 출력 토큰 한도

커스텀 출력 토큰 한도가 설정된 모델은 사용자의 프론트엔드가 더 큰 출력 토큰 값을 요청하더라도 FocusAway가 해당 한도 이하로 낮춰서 업스트림에 전달합니다.

### 티어 관리

FocusAway에는 기본 회원 티어가 있으며, 초기 이름은 `Tier 0`입니다.

관리자는 다음을 할 수 있습니다.

- 티어 생성
- 티어 이름 변경
- 티어 순서 변경
- 기본 티어가 아닌 티어 삭제
- 티어별 주간 충전량 설정
- 회원별 티어 변경

고정된 관리자 표시 티어는 일반 DB 관리 대상 회원 티어와 별개입니다.

### 할당량 관리

주간 잔액은 설정된 타임존 기준 매주 월요일 0시에 티어별 주간 충전량으로 초기화됩니다. 더해지는 것이 아니라 지정값으로 초기화됩니다.

보너스 잔액은 별도로 유지되며 주간 초기화로 사라지지 않습니다.

요청 비용은 주간 잔액에서 먼저 차감되고, 부족하면 보너스 잔액에서 차감됩니다.

관리자 계정은 어떤 모델을 사용해도 차감되지 않습니다.

### 회원 관리

관리자는 다음을 할 수 있습니다.

- 회원 정지
- 회원 강제 삭제
- 회원 티어 변경
- 전체 회원 보너스 잔액 지급
- 특정 접속 아이디에 보너스 잔액 지급
- 회원별 마지막 접속 IP 확인

### 회원가입 제어

서비스 설정에서 회원가입을 열거나 닫을 수 있습니다.

회원가입이 닫혀 있으면 회원가입 버튼이 보이지 않고, `/signup`으로 직접 접근해도 가입 불가 안내가 표시됩니다.

### 자동 승격

기본 티어가 아닌 일반 티어가 하나 이상 있을 때 자동 승격 설정을 사용할 수 있습니다.

지원 조건:

- 가입 후 일정 시간 경과
- 가입 후 프리미엄 요청 누적 사용량 일정 이상

여러 조건을 켠 경우 현재 동작은 OR입니다. 선택된 조건 중 하나라도 만족하면 승격됩니다.

## 사용자 API 설명서

주요 지원 라우트:

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/completions`
- `POST /v1/responses`
- `POST /v1/embeddings`
- `POST /v1/images/generations`
- `POST /v1/audio/speech`

`GET /v1/models`는 인증된 API 사용자가 실제로 사용할 수 있는 모델만 반환합니다.

비용이 부과되는 POST 라우트는 업스트림에 전달되기 전에 모델별 1회 비용을 차감합니다.

스트리밍은 호환되는 업스트림과 클라이언트에서 지원됩니다. TTS 음성 응답은 전체 파일을 메모리에 버퍼링하지 않고 바이너리 청크로 전달됩니다. 다만 OpenAI 호환 백엔드마다 이벤트 형식이 조금씩 다를 수 있습니다. 모델 목록은 뜨는데 채팅이 실패하면 stream 모드와 non-stream 모드를 모두 확인하세요.

TTS는 JSON 요청을 사용하는 `POST /v1/audio/speech`를 지원합니다. 요청의 모델은 먼저 업스트림 모델 목록과 동기화되어 있어야 하며, 다른 과금 대상 API와 동일하게 모델별 1회 비용과 티어 접근 정책이 적용됩니다. 음성 인식용 multipart 엔드포인트인 `/v1/audio/transcriptions`는 현재 지원 범위에 포함되지 않습니다.

## 설정

런처는 프로젝트 루트에 `focusaway-config.json`을 저장합니다.

예시:

```json
{
  "host": "127.0.0.1",
  "port": 8787,
  "timezone": "Asia/Seoul",
  "database_path": "focusaway.db",
  "max_request_bytes": 10485760,
  "cors_allowed_origins": "http://127.0.0.1:3000,http://localhost:3000",
  "upstream_base_url": "http://127.0.0.1:11434",
  "upstream_api_prefix": "/v1",
  "upstream_models_path": "/v1/models",
  "upstream_api_key": "enc:v1:...",
  "upstream_auth_mode": "bearer",
  "upstream_auth_header": "Authorization",
  "upstream_auth_scheme": "Bearer",
  "upstream_extra_headers": "",
  "upstream_timeout_seconds": 300,
  "session_hours": 168,
  "signup_cooldown_seconds": 3600,
  "carrier_signup_cooldown_seconds": 600,
  "trusted_proxy_cidrs": "127.0.0.1/32,::1/128",
  "app_name": "FocusAway",
  "operator_name": "FocusAway 운영자",
  "contact_email": "operator@example.com",
  "contact_address": ""
}
```

주요 항목:

- `cors_allowed_origins`: 공개 운영 시 신뢰하는 프론트엔드 Origin만 허용하세요.
- `upstream_base_url`: 업스트림 백엔드 루트 주소.
- `upstream_api_prefix`: 프록시 API 경로 prefix.
- `upstream_models_path`: 모델 목록 endpoint.
- `upstream_auth_mode`: `bearer`, `header`, `x-api-key`, `none`.
- `upstream_auth_header`: 인증 헤더 이름.
- `upstream_auth_scheme`: bearer류 인증 스킴.
- `upstream_extra_headers`: 추가 고정 헤더 JSON 문자열.
- `signup_cooldown_seconds`: 일반 IP에서 성공한 가입 후 동일 IP의 재가입 대기시간(초). 기본 3600초.
- `carrier_signup_cooldown_seconds`: 한국 통신 3사 LTE/5G 대역의 재가입 대기시간(초). 기본 600초.
- `carrier_ip_ranges`: 내장 통신사 IPv4/IPv6 대역을 대체할 쉼표 구분 CIDR 또는 `시작IP-끝IP` 목록. 보통은 생략합니다.
- `trusted_proxy_cidrs`: `X-Forwarded-*`를 신뢰할 직접 연결 프록시 대역. 기본값은 로컬 프록시만 허용합니다.

## 업스트림 API 키 암호화

`upstream_api_key`는 `focusaway-config.json`에 암호화되어 저장됩니다.

FocusAway는 다음 순서로 암호화 마스터 키를 선택합니다.

1. `FOCUSAWAY_SECRET_KEY` 환경변수가 있으면 그것을 사용합니다.
2. 없으면 config 파일 옆에 `focusaway-secret.key`를 자동 생성해서 사용합니다.

기존 평문 업스트림 API 키는 config 로드 시 자동으로 암호문으로 마이그레이션됩니다.

기존 설치본을 다른 머신으로 옮길 때는 암호화된 config와 그에 맞는 `focusaway-secret.key`를 함께 옮기거나, 같은 `FOCUSAWAY_SECRET_KEY`를 유지해야 합니다.

마스터 키를 잃어버리면 암호화된 업스트림 API 키는 복구할 수 없습니다. 이 경우 런처에서 업스트림 API 키를 다시 입력하세요.

## 보안 참고

- 비밀번호는 평문 저장되지 않습니다.
- 세션 쿠키는 `HttpOnly`, `SameSite=Lax`를 사용합니다.
- 세션 인증 POST 작업에는 CSRF 보호가 적용됩니다.
- 로그인 시도 제한은 IP 기준 메모리에서 관리됩니다.
- 정지된 사용자는 웹/API 인증이 차단됩니다.
- 업스트림 에러 본문은 사용자에게 직접 전달되지 않습니다.
- config, SQLite DB, 로컬 secret key 파일은 `0600` 권한 설정을 시도합니다.
- `X-Forwarded-*` 헤더는 직접 연결한 상대가 `trusted_proxy_cidrs`에 포함될 때만 신뢰합니다. 공개 프록시 주소를 광범위하게 등록하지 마세요.
- 회원가입 쿨타임은 성공한 가입을 기준으로 일반 IP 60분, 통신 3사 모바일 IP 10분이 기본값입니다. 환경변수 `FOCUSAWAY_SIGNUP_COOLDOWN_SECONDS`, `FOCUSAWAY_CARRIER_SIGNUP_COOLDOWN_SECONDS`, `FOCUSAWAY_CARRIER_IP_RANGES`로 조정할 수 있습니다.
- 공개 운영 시 `cors_allowed_origins`를 신뢰하는 프론트엔드 주소로 제한하세요.
- 완전히 새 DB에서는 첫 가입자가 관리자가 됩니다. 서비스를 공개하기 전에 먼저 관리자 계정을 생성하세요.

## 플랫폼별 참고

- macOS: `FocusAway.command` 또는 `python3 launcher.py`.
- Linux: Tk가 있으면 `python3 launcher.py`, 서버만 쓰려면 `python3 app.py`.
- Windows: `FocusAway.bat` 또는 `py launcher.py`.

## 문제 해결

- 런처가 열리지 않음: 터미널에서 `python3 launcher.py`를 실행하고 `focusaway-launcher.log`를 확인하세요.
- 서버가 시작되지 않음: `focusaway-server.log`를 확인하세요.
- 프론트엔드에서 모델을 불러오지 못함: API 주소, `/v1` 처리, CORS Origin, 사용자 API 키를 확인하세요.
- 모델이 누락됨: 관리자 패널에서 모델 새로고침을 실행하고 assistant 모델 필터링 옵션을 확인하세요.
- 모델 목록은 뜨지만 채팅이 실패함: stream 모드와 non-stream 모드를 모두 확인하세요.
- 암호화된 업스트림 키를 로드하지 못함: `FOCUSAWAY_SECRET_KEY` 또는 `focusaway-secret.key`가 맞는지 확인하세요.

## 배포용 사본

깨끗한 배포용 사본에는 다음을 포함하지 않는 것이 좋습니다.

- `focusaway.db`
- `focusaway-config.json`
- `focusaway-secret.key`
- 로그 파일
- 백업 DB
- `__pycache__`
- `.git`

새 배포에서는 `focusaway-config.example.json`을 시작점으로 사용하세요.
