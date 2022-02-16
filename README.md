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

## Input格式與內容

### Virtual Network

virtual network中的node本身就是一個2-integer tuple 表示`(x, y)`這樣寫起來比較方便，但`x`、`y`的attribute還是保留。

Attributes:
- Node
  - `x`, `y`: 該點的坐標
- Edge
  - `length`: 長度。
  - `score`: 將自己(這個edge)代入新的(2)式計算後的結果。
  - $\text{score} = O_d(e_i)$


### Physical Network

一個上面有障礙物的棋盤，沒有障礙物的格子對應一個node，從這個格子可用皇后的走法走到的其他格子(不包含自己)都是它的鄰居。

## 實作進度與細節

- Dataset的讀取/前處理
- Find Virtual World Path
  - 前處理
  - Initialization
  - Expansion
- Find Physical World Path
- 輸出結果

### Dataset的讀取/前處理

將dataset讀入後轉換成上述的格式。

### Find Virtual World Path

跟主要演算法有關的code都在`main.py`裡

#### 1. 前處理: 計算"demand"和"score"

因為「轉換機制」，反正它就是某個公式算出來的分數。由`computeScore`處理，給road network加上"score"。

#### 2. Initialization

`getCandidateEdges`回傳$L_d$，因為不考慮connetivity，它同時也是$L_e$。我寫了一個class `SortedEdgeScoreList`實作它。

$K$設為transit network的node數量和candidate edges的總數取最小值。

Priority queue實作在`pq.py`的`MyPQ`。

#### 3. Expansion

進while loop後開始expansion，因為不考慮connectivity的關係，每一次expansion就是從鄰居中找在$L_d$裡面排最前的那個。

與計算夾角和距離有關的函數都放在`geo.py`。

一些狀況：
- 會發生beginning edge和ending edge是同一個的狀況，根據paper第3頁的註解4，頭尾相連的環形路線是允許的。目前的設計是`be == ee`的路線可作為$\mu$的候選路線，但不能expand。
- paper給的algorithm裡面，$tn(cp)$和$\mu$的更新的先後順序很奇怪？它先更新$\mu$，然後檢查$tn(cp) < Tn$後進入verification，然後在verification**裡面**才更新$tn(cp)$。但因為它一次expand兩端，所以假設原本$tn(cp) = Tn-1$，然後expand的兩端都+1，這樣push到Q裡面的時候已經是$Tn+1$了。等到它pop出來時還可以再兩端expand一次，這樣$\mu$的候選路徑會出現$tn(cp) = Tn+3$的情況
- 我目前把順序改成: 更新$\mu$ -> 更新$tn(cp)$ -> 檢查$tn(cp) < Tn$ -> verification

### Find Physical World Path

考慮了virtual路徑的「正」、「反」兩種走法，並對所有physical world的項點都做一次稍微改動過的Dijkstra，找出全部可能性中的最小cost路徑。

改動:
- 拿掉了不找已經檢查過的node的在「鬆弛」時的限制，因為edge cost會隨走到這個node的時間和上一個node而有變化
- 如果cost已經大於已知的最小cost就不繼續走
- 如果路徑長度等於virtual路徑長度則停止並更新最小cost路徑和最小cost

<!--

<style>math {font-weight: bold; font-family: 'Cambria', 'Times New Roman';}</style>

偽代碼:
<div style='white-space: pre;'><b>Input:</b> virtual world path, physical world network
Initialize <math>bestPath</math> as empty sequence, <math>minCost</math> as infinity
For <math>virtualPath</math> from two different walking direction of virtual world path
    For each <math>n</math> in phyiscal world network's nodes
        Initialize <math>d</math> and <math>Q</math>
        Add sequence <math>(n)</math> into <math>Q</math>
        While <math>Q</math> is not empty
            <math>q</math> := sequence with minimal cost in <math>Q</math>
            <math>u</math> := last member of <math>q</math>
            For <math>v</math> in <math>u</math>'s neighbors
                Calculate <math>cost</math> from <math>u</math> to <math>v</math> in respect to <math>q</math> and <math>virtualPath</math>
                If <math>d[v] > d[u] + cost</math>
                    <math>q'</math> := <math>q</math> append <math>v</math> 
                    <math>d[v] := d[u] + cost</math>
                    If <math>d[v] < minCost</math>
                        If <math>q'</math> has same length as <math>virtualPath</math>
                            <math>bestPath := q'</math>
                            <math>minCost := d[v]</math>
                        Else
                            Add <math>q'</math> into <math>Q</math> with cost of <math>d[v]</math>
<b>Return:</b> <math>bestPath</math>, <math>minCost</math>
</div>

-->

### 輸出結果

`out.py`裡的`outputResult`是測試時為了能較好看出程式問題而讓它輸出圖片。

最新的圖片輸出結果:

![](https://i.imgur.com/5wcKFb7.png)
--------
![](https://i.imgur.com/q05VKcG.png)
--------
![](https://i.imgur.com/4CZhALm.png)
--------
![](https://i.imgur.com/JtR0kqO.png)

實際的輸出格式還待後續要求。