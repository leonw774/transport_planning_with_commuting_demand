# Transport Planning with Commuting Demand

https://github.com/leonw774/transport_planning_with_commuting_demand/tree/dual-world

[TOC]

## 新的(2022/02/19之後)運作流程

### Inputs

- A virtual world graph. $G_v = (V_v, E_v)$ is a **connected graph**
  - each vertex is a 2d vector
  - the length of an edge is defined as the distance between the two vertices. $e = (u, v)$. $|e| = \text{dist}(u, v)$
- A physical world graph. $G_p = (V_p, E_p)$ is a **connected graph**
  - every vertex is a 2d vector
- A mapping from virtual world vertex to physical world vertex. $m_{vp}: V_v \rightarrow V_p$
- Source point: a virtual world vertex. $s \in V_v$
- Destination points: a set of virtual world vertices. $v_d \subseteq V_v$
- A cost function: $\text{cost} : (E_v; E_p, m_{vp}) \rightarrow \mathbb{R}^+$, 

### Hyperparameters

- $0 \leq \alpha \leq 1$
- parameters from original algorithm
  - $sn$, $itmax$
  - $Tn$設為無限，不再成為可輸入的參數

### Transformed virtual world

我們要先對virtual world graph做一個轉換再把它餵進這個演算法。

We define $G_v' = (V_v', E_v')$ as a **complete graph** where $V_v' = v_d \cup \{s\}$.

Let $|e'|$ be the weight of edge $e' = (u, v) \in E_v'$,

$$ |e'| = \underset{p}{min} \left( \sum_{e_p \in p} \alpha |e_p|  + (1 - \alpha) \text{cost}(e_p; E_p, m_{vp}) \right) 
$$

where $p$ is a path on $G_v$ that start from $u$ and end on $v$, $e_p$ is an edge in $p$.

We also record the path $p_{e'}$ that correponded to $|e'|$ for each edge $e'$. We are sure that such path exists because $G_v$ is a connected graph.

### Run the algorithm on transformed virtual world

對原本的演算法做了一些修改

1. (2)式修改成： $O_d(\mu) = \sum_{e' \in \mu} - |e'|$。因為這個演算法會找最大值，而我們希望路徑的weight愈小愈好。

2. 不考慮Connectivity

3. 要全部的vertex都走到才算是合格的輸出路徑

## Input格式與內容

### Virtual network

讓virtual network中的node本身就是一個2-integer tuple 表示`(x, y)`這樣寫起來比較方便。

Attributes:
- Node
  - `phy`: 對應的physical world graph node = $m_{vp}(v)$
- Edge
  - `length` = $|e|$
  - `cost` = $\text{cost}(e; E_p, m_{vp})$
  - `weight` = $\alpha |e| + (1 - \alpha) \text{cost}(e; E_p, m_{vp})$

### Tranformed virtual network

Attributes:
- Edge
  - `weight` = $-|e'|$
  - `path` = $p_{e'}$

### Physical network

一個上面有障礙物的棋盤，沒有障礙物的格子對應一個node，從這個格子可用皇后的走法走到的其他格子(不包含自己)都是它的鄰居。

## 實作規劃/進度/細節

### Dataset的讀取/前處理

將dataset讀入後轉換成上述的格式。

- `getVirtual(path: str, vpmap_path:str) -> nx.Graph:`
  - 讀入virtual network
  - 讀入`tophy`檔，取得:
    - 每個點在physical的對應
    - 每個邊的`length`和`cost`
    - `source`和`destinations`

- `getPhysical(path: str) -> nx.Graph:`
  - 讀入physical network

- `makeTransformedVirtual(vrNet: nx.Graph, source: tuple, destnations: set, alpha: float) -> nx.Graph:`
  - 建出transformed virtual world的network：頂點只有`source`和`destinations`的complete graph
  - 用`alpha`給virtual world算出每一個edge的`weight`
  - 找出virtual network上(`source`+`destinations`)兩兩之間的最小weight/最小weight路徑，分別成為transformed virtual network的`weight`和`path`

### Find virtual graph path

``` python
def findTransformedVirtualPath(tfvrNet: nx.Graph, sn: int, itmax: int) -> list
```

回傳list of vertices

#### Initialization

`getCandidateEdges`回傳$L_d$，因為不考慮connetivity，它同時也是$L_e$。我寫了一個class `SortedEdgeScoreList`實作它。

$K$設為transit network的node數量和candidate edges的總數取最小值。

Priority queue實作在`pq.py`的`MyPQ`。

#### Expansion-based Traversal Algorithm

進while loop後開始expansion，因為不考慮connectivity的關係，每一次expansion就是從鄰居中找在$L_d$裡面排最前的那個。

#### 一些狀況

- 為了讓找到的路線可以是環形路線，目前的設計是讓`be == ee`的路線可作為$\mu$的候選路線，但不能expand。
- 無法達成「要全部的vertex都走到才算是合格的輸出路徑」。可能是因為Algorithm 1的Line5-6，當$O^{\uparrow}(cp) \leq O_{max}$時會break loop。但把它拿掉後仍然有時無法將全部的vertex都走到，目前不知道是什麼原因。
- 如果無法將全部的vertex都走到就報錯

### Convert transformed virtual path into virtual path and physical path

``` python
def getVirtualAndPhysicalPath(tfvrNet: nx.Graph, vrNet: nx.Graph, tfvrPath: list, source):
```

1. 把找到的tfvrNet的上的path中的每一個edge的`path`接起來就是vrPath
2. 用virtual network的`phy`把vrPath轉換成phPath
   - 兩個physical vertex之間找dijkstra最短路徑，然後接起來
3. 從vrPath算出totalCost
4. `return vrPath, phPath, totalCost, totalLength`

### 輸出結果

寫在`out.py`裡

``` python
def outputJSON(vrPath: list, totalCost: float, totalLength: float, vrNet: nx.Graph, source, destinations, args):
```

正式JSON格式，檔名為`args.output + '_path.json'`

``` python
def outputImage(
    vrPath: list, totalCost: float, totalLength: float, vrNet: nx.Graph, source, destinations,
    phPath:list, phWorldL: int, phWorldW: int, obs: list, args):
```

這是為了測試時能較好看出程式問題而讓它輸出圖片，檔名為`args.output + '_img.png'`
