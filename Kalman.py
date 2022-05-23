'''
@name kalman_filter
@variables
- est_x: last estimated state
- y: last READ output
- P: covariance of the error
- H: output-state matrix
- R: chosen by us -> noise covariance (measured 0.0026)
- Q: chosen by us -> initial estimated covariance (of the state(?))
'''


def kalman_filter(est_x, y, P, H, R, Q):
    K = (P*H)/(H*P*H+R)
    est_x = est_x+K*(y-H*est_x)
    P = (1-K*H)*P+Q
    return (est_x ,P) 


