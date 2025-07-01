[해솔]
A. LLM의 Next Token 확률 분포 활용

[현민]
B. Slice된 입력 데이터에 대한 Next Token 확률 엔트로피 분석
> 전제: Transformer 모델의 내재적인 정보처리 패턴이 있다

1. RLHF 점수 예측 (Reverse RLHF)
- 혹은 여러 리워드 모델
- 전체 트레인 데이터셋에 대해 우리가 직접 선호도를 측정해서 추가 라벨 증강

[동연]
C. Perplexity 기반

3. 도메인 혼재 여부 파악
- 인간 한 사람은 여러 지식을 한번에 다 알지 못함

[채민]
D. 텍스트를 두 부분으로 자른 후 앞부분을 통해 생성된 데이터와 원래 뒷부분을 스코어 계산

[채운]
E. TTT-Linear에 뒤에 분류기

4. Test-time Adaptation (Token 순서 재정렬 태스크)
- 모델이 인풋 텍스트 재정렬 성공까지 몇 회의 Adaptation이 필요한지 측정

2. Surprise Metric or Memory Compression 정도 측정
- 혹은 논리적 모순 탐지

5. Reverse Speculative Decoding
- 작은 모델이 얼마나 해당 텍스트를 큰 모델만큼 예측할 수 있는가

* 새로운 LLM이 등장한 경우에 대응하기 위한 Test-time Adaptation
- ?