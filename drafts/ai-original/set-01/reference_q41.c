#include <stddef.h>
typedef struct Node { int key; struct Node *next; } Node;
int longestCommonRun(const Node *a, const Node *b, int *lo, int *hi)
{
    const Node *p = a, *q = b;
    int prev = 0, start = 0, len = 0;
    int best = 0, bestLo = 0, bestHi = 0;

    while (p != NULL && q != NULL) {
        if (p->key < q->key) {
            int v = p->key;
            do { p = p->next; } while (p != NULL && p->key == v);
        } else if (p->key > q->key) {
            int v = q->key;
            do { q = q->next; } while (q != NULL && q->key == v);
        } else {
            int v = p->key;               /* 一个新的公共值 */
            if (len > 0 && v == prev + 1)
                ++len;
            else {
                start = v;
                len = 1;
            }
            prev = v;
            if (len > best || (len == best && start < bestLo)) {
                best = len;
                bestLo = start;
                bestHi = v;
            }
            do { p = p->next; } while (p != NULL && p->key == v);
            do { q = q->next; } while (q != NULL && q->key == v);
        }
    }
    if (best > 0) {
        *lo = bestLo;
        *hi = bestHi;
    }
    return best;
}
