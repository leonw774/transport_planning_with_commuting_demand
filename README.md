# Transport Planning with Commuting Demand

https://github.com/leonw774/transport_planning_with_commuting_demand

[TOC]

## 與paper不同的地方

### 1. The commuting demand that can be met by 𝜇

修改過後的(2)式：

$$ O_d(\mu) = \sum_{e \in \mu} |e| (max_{e' \in E}(|e'|) - |e|) 
$$

where $|e|$ denotes the *length* of edge $e \in E$.

### 2. 不考慮Connectivity

因此"Lanczos-based Connectivity Estimation"等等的東西通通用不上

## (拿到正式的dataset後的)Input格式與內容

原本有三個input分別是:
- Road Network
- Transit Network
- Trajectory Data

因為正式的dataset要求road network和transit network一模一樣，且沒有trajectory data，所有東西就往road network上塞吧。

### Road Network

讓road network中的node本身就是一個2-integer tuple這樣寫起來比較方便，但保留`x`、`y`。

原本的transit net的`path`不需要了，刪除。

Attributes:
- Node
  - `x`, `y`: 該點的坐標
- Edge
  - `length`: 長度。
  - `score`: 將自己(這個edge)代入新的(2)式計算後的結果。
  - $e_i[\text{score}] = O_d(e_i)$

因為無法預測Transit Network的來源會是什麼，就當作所有attribute在輸入前都已經先預處理好了。

### Transit Network

(已不需要)

### Trajectory Data

(已不需要)

## 實作進度與細節

- dataset的讀取/前處理
- ~~臨時的測試用dataset~~
- 主要演算法
- 輸出結果

### dataset的讀取/前處理

將dataset讀入後轉換成上述的格式。

### 臨時的測試用dataset

(已不需要)

### 主要演算法

跟主要演算法有關的code都在`main.py`裡

#### 1. 前處理: 計算"demand"和"score"

因為「轉換機制」，反正它就是某個公式算出來的分數。由`computeDemand`處理，給road network加上"demand"和"score"。

#### 2. Initialization

`getCandidateEdges`回傳$L_d$，因為不考慮connetivity，它同時也是$L_e$。我寫了一個class `SortedEdgeDemandList`實作它。

$K$設為transit network的node數量和candidate edges的總數取最小值。

Priority queue實作在`pq.py`的`MyPQ`。

#### 3. Expansion

進while loop後開始expansion，因為不考慮connectivity的關係，每一次expansion就是從鄰居中找在$L_d$裡面排最前的那個。

與計算夾角和距離有關的函數都放在`geo.py`。

一些狀況：
- 會發生beginning edge和ending edge是同一個的狀況，根據paper第3頁的註解4，頭尾相連的環形路線是允許的。目前的設計是`be == ee`的路線可作為$\mu$的候選路線，但不能expand。
- paper給的algorithm裡面，$tn(cp)$和$\mu$的更新的先後順序很奇怪？它先更新$\mu$，然後檢查$tn(cp) < Tn$後進入verification，然後在verification**裡面**才更新$tn(cp)$。但因為它一次expand兩端，所以假設原本$tn(cp) = Tn-1$，然後expand的兩端都+1，這樣push到Q裡面的時候已經是$Tn+1$了。等到它pop出來時還可以再兩端expand一次，這樣$\mu$的候選路徑會出現$tn(cp) = Tn+3$的情況
- 我目前把順序改成: 更新$\mu$ -> 更新$tn(cp)$ -> 檢查$tn(cp) < Tn$ -> verification

### 輸出結果

`out.py`裡的`outputResult`是測試時為了能較好看出程式問題而讓它輸出圖片。

正式dataset的`Exp1-G20_vindex.txt`的圖片輸出結果:

![](https://i.imgur.com/QYazSgH.png)

實際的輸出格式還待後續要求。