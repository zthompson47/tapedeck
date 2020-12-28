pub mod logging;
pub mod shell;

#[allow(unused_imports)]
use {async_std::task, smol::Task, std::time::Duration};

pub struct WaitGroup {
    #[allow(dead_code)]
    tasks: Vec<smol::Task<()>>,
}

impl Default for WaitGroup {
    fn default() -> Self {
        Self { tasks: Vec::new() }
    }
}

impl WaitGroup {
    pub fn new() -> Self {
        Self::default()
    }

    pub async fn join(self) {
        task::sleep(Duration::from_millis(2000)).await;
    }
}

impl Clone for WaitGroup {
    fn clone(&self) -> WaitGroup {
        WaitGroup { tasks: Vec::new() }
    }
}

#[macro_export]
macro_rules! async_wait_group {
    ( $( $x:expr ),+ ) => {
        let original_wg = WaitGroup::new();
        $(
            let wg = original_wg.clone();
            println!("before spawn...");
            smol::spawn(async move {
                info!("----->>>>>>>>>>>>>>>  in macro");
                let result = $x().await;
                info!("----->>>>>>>>>>>>>>>  in macro: after await closure");
                println!("{:?}", result);
                drop(wg);
            }).detach();
            println!("after spawn...");
        )*
        println!("------before wait--------------");
        original_wg.join().await;
        println!("------after wait--------------");
    }
}
