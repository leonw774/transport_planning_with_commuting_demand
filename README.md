# Transport Planning with Commuting Demand

https://github.com/leonw774/transport_planning_with_commuting_demand

[TOC]

## 新的(2022/02/19)運作流程

### INPUTS

- A virtual world graph. $G_v = (V_v, E_v)$ is a **connected graph**
  - each vertex is a 2d vector
  - the length of an edge is defined as the distance between the two vertices. $e = (u, v)$. $|e| = \text{dist}(u, v)$
- A physical world graph. $G_p = (V_p, E_p)$ is a **connected graph**
  - every vertex is a 2d vector
- A mapping from virtual world vertex to physical world vertex. $m_{vp}: V_v \rightarrow V_p$
- Source point: a virtual world vertex. $s \in V_v$
- Destination points: a set of virtual world vertices. $v_d \subseteq V_v$
- A cost function: $\text{cost} : E_v; E_p, m_{vp} \rightarrow \reals^+$, 

### PARAMETERS

- $0 \leq \alpha \leq 1$
- parameters from original algorithm
  - $Tn$, $sn$, $itmax$
  - $Tn$設為無限

### TRANFORMATION OF THE VIRTUAL WORLD

我們要先對virtual world graph做一個轉換再把它餵進這個演算法。

We define $G_v' = (V_v', E_v')$ as a **complete graph** where $V_v' = v_d \cup \{s\}$.

Let $|e'|$ be the weight of edge $e' = (u, v) \in E_v'$,

$$ |e'| = \underset{p}{min} \left( \sum_{e_p \in p} \alpha (max_{e_v \in E_v}(|e_v|) - |e_p|)  + (1 - \alpha) \text{cost}(e_p; E_p, m_{vp}) \right) 
$$

where $p$ is a path on $G_v$ that start from $u$ and end on $v$, $e_p$ is an edge in $p$.

We also record the path $p_{e'}$ that correponded to $|e'|$ for each edge $e'$. We are sure that such path exists because $G_v$ is a connected graph.

### RUN THE ALGORITHM ON TRANFORMED VIRTUAL WORLD

對原本的演算法做了一些修改

1. (2)式修改成：

$$ O_d(\mu) = \sum_{e' \in \mu} |e'|
$$

2. 不考慮Connectivity

3. 要全部的vertex都走到才算是合格的輸出路徑

## Input格式與內容

### Virtual Network

讓virtual network中的node本身就是一個2-integer tuple 表示`(x, y)`這樣寫起來比較方便。

Attributes:
- Node
  - `phy`: 對應的physical world graph node
- Edge
  - `length` = $|e|$

### Tranformed Virtual Network

Attributes:
- Edge
  - `weight`: $|e'|$
  - `path`: $p_{e'}$

### Physical Network

一個上面有障礙物的棋盤，沒有障礙物的格子對應一個node，從這個格子可用皇后的走法走到的其他格子(不包含自己)都是它的鄰居。

## 實作進度與細節

### Dataset的讀取/前處理

將dataset讀入後轉換成上述的格式。

重寫:
- `getVirtual(path: str) -> nx.Graph`: 讀入virtual network
- `getPhysical(path: str) -> nx.Graph`: 讀入physical network

新增:
- `makeTransformedVirtual(vrNet: nx.Graph, source: tuple, destnations: set, phNet: nx.Graph, costFunc: Callable) -> nx.Graph`

### Find Virtual Graph Path

`findVirtualPath(vrNet: nx.Graph, tfvrNet: nx.Graph, Tn: int, sn: int, itmax: int) -> list, float`

return path, totalWeight

在`tfvrNet`上找路徑，然後轉換回`vrNet`上的路徑

#### Initialization

`getCandidateEdges`回傳$L_d$，因為不考慮connetivity，它同時也是$L_e$。我寫了一個class `SortedEdgeScoreList`實作它。

$K$設為transit network的node數量和candidate edges的總數取最小值。

Priority queue實作在`pq.py`的`MyPQ`。

#### Expansion

進while loop後開始expansion，因為不考慮connectivity的關係，每一次expansion就是從鄰居中找在$L_d$裡面排最前的那個。

與計算夾角和距離有關的函數都放在`geo.py`。雖然$Tn$設成無限之後就不需要計算夾角了但還是先留著誰知道以後用不用得上。

不知道要怎麼達成「要全部的vertex都走到才算是合格的輸出路徑」，因為Algorithm 1的Line5-6，當$O^{\uparrow}(cp) \leq max$時會break loop。把它拿掉嗎？

一些狀況:
- 會發生beginning edge和ending edge是同一個的狀況，根據paper第3頁的註解4，頭尾相連的環形路線是允許的。目前的設計是`be == ee`的路線可作為$\mu$的候選路線，但不能expand。
- paper給的algorithm裡面，$tn(cp)$和$\mu$的更新的先後順序很奇怪？它先更新$\mu$，然後檢查$tn(cp) < Tn$後進入verification，然後在verification**裡面**才更新$tn(cp)$。但因為它一次expand兩端，所以假設原本$tn(cp) = Tn-1$，然後expand的兩端都+1，這樣push到Q裡面的時候已經是$Tn+1$了。等到它pop出來時還可以再兩端expand一次，這樣$\mu$的候選路徑會出現$tn(cp) = Tn+3$的情況
- 我目前把順序改成: 更新$\mu$ -> 更新$tn(cp)$ -> 檢查$tn(cp) < Tn$ -> verification

#### (新增) Transformed back to virtual world path

把找到的tfvrNet的上的path中的每一個edge的`path`接起來就是了。

### (重寫) Find Physical World Path

直接用virtual network上的`phy`就可以把virtual path轉換成physical path

<!-- ### 檢查cost limit

如果有cost limit，就會建一個blocked edges tree，然後對它做level order traverse，每個node是virtual world edge的集合，root是空集合。走到一個node時會將在node裡的virtual world edge score設成負無限大，然後找virtual路徑和physical路徑。找完後後檢查physical路徑的cost是否大於cost limit。如果超過，設virtual路徑上有n個edges，這個node底下就會分出n個children node：$\text{childNodes} = \{ \text{node} \cup \{e\} \ | \ \forall e \in \text{edges of virtual path} \}$。

每traverse完一個level就會檢查是否找到了不超過cost limit的physical路徑，找到了就停止尋找，否則繼續到下一個level。 -->

### 輸出結果

`out.py`裡的`outputResult`是測試時為了能較好看出程式問題而讓它輸出圖片。

我自己加了一個較大的physical空間:phy-big.txt，可以看到更清楚的輸出結果。

最新的圖片輸出結果: 

(尚無)

實際的輸出格式還待後續要求。