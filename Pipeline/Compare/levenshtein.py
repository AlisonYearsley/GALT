

def levenshtein(str1,str2):
    n = len(str1)
    m = len(str2)
    dp = [[0 for _ in range(m+1)] for _ in range(n+1)]
    for i in range(n+1):
        dp[i][0] = i
    for j in range(m+1):
        dp[0][j] = j
    
    for i in range(1,n+1):
        for j in range(1,m+1):
            options = [dp[i-1][j]+1,dp[i][j-1]+1]
            if str1[i-1] == str2[j-1]:
                options.append(dp[i-1][j-1])
            dp[i][j] = min(options)
    return dp[-1][-1]

print(levenshtein("INTENTION","EXECUTION"))