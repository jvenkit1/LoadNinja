package main

import(
	"errors"
	"github.com/sirupsen/logrus"
	"net/http"
	"strconv"
	"time"
)
/*
Client must spawn off multiple requests with each request in a separate thread.
Obtain total number of requests and endpoint as parameters

Now, for each request, if the request fails, server will return a backoff. Retry after the value mentioned in backoff has elapsed

Request contains the following
1. UserPriority - Free/Paid (String)
2. API Priority - Low, Medium, High (String)


Log:
In a CSV write, user - Free/Paid, API Priority and Latency

3 Things to be added:
1. Mechanism on spawning threads
2. Add request headers -- DONE
3. Add logging statements
4. Add latency measurements - Simple Thread.time the start and end of the call
 */


// send requests as a goroutine
func sendRequest(retries int, endPoint string) error{

	if retries == 0 {
		return errors.New("retry count exceeded. Not serving requests anymore")
	}
	tr := &http.Transport{
		MaxIdleConns:       100,
		IdleConnTimeout:    1 * time.Second,
	}
	client := &http.Client{Transport: tr}

	req, err := http.NewRequest(http.MethodGet, endPoint, nil)
	if err != nil {
		logrus.WithError(err).Error("couldn't construct http request")
	}
	req.Header.Set("user-type", "user-free")
	req.Header.Set("request-type", "priority-low")

	resp, err := client.Do(req)
	if err != nil {
		logrus.WithError(err).Error("Failed to send http request")
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		backoff, err := strconv.ParseFloat(resp.Header.Get("Backoff"), 64)
		if err != nil {
			logrus.WithError(err).Error("Error reading the backoff value")
		}
		time.Sleep(time.Duration(backoff) * time.Millisecond)
		return sendRequest(retries-1, endPoint)
	} else {

	}
	return nil
}

func main(){
	logrus.Info("Hello World")
}